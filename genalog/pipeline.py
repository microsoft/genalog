from genalog.generation.document import DocumentGenerator
from genalog.generation.document import DEFAULT_STYLE_COMBINATION
from genalog.generation.content import CompositeContent, ContentType
from genalog.degradation.degrader import Degrader, ImageState
from json import JSONEncoder
from tqdm import tqdm

import concurrent.futures
import timeit
import cv2
import os


class ImageStateEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ImageState):
            return obj.value
        return JSONEncoder.default(self, obj)


class AnalogDocumentGeneration(object):
    def __init__(
        self,
        template_path=None,
        styles=DEFAULT_STYLE_COMBINATION,
        degradations=[],
        resolution=300,
    ):
        self.doc_generator = DocumentGenerator(template_path=template_path)
        self.doc_generator.set_styles_to_generate(styles)
        self.degrader = Degrader(degradations)

        self.resolution = resolution

    def list_templates(self):
        """List available templates to generate documents from

        Returns:
            list -- a list of template names
        """
        return self.doc_generator.template_list

    def generate_img(self, full_text_path, template, target_folder=None):
        """Generate synthetic images given the filepath of a text document

        Arguments:
            full_text_path {str} -- full filepath of a text document (i.e /dataset/doc.txt)
            template {str} -- name of html template to generate document from
                Ex: "text_block.html.jinja"

        Keyword Arguments:
            target_folder {str} -- folder path in which the generated images are stored
                (default: {None})
            resolution {int} -- resolution in dpi (default: {300})
        """
        with open(full_text_path, "r", encoding="utf8") as f:  # read file
            text = f.read()
        content = CompositeContent([text], [ContentType.PARAGRAPH])

        generator = self.doc_generator.create_generator(content, [template])
        # Generate the image
        doc = next(generator)
        src = doc.render_array(resolution=self.resolution, channel="GRAYSCALE")
        # Degrade the image
        dst = self.degrader.apply_effects(src)

        if not target_folder:
            # return the analog document as numpy.ndarray
            return dst
        else:
            # save it onto disk
            text_filename = os.path.basename(full_text_path)
            img_filename = text_filename.replace(".txt", ".png")
            img_dst_path = target_folder + "img/" + img_filename
            cv2.imwrite(img_dst_path, dst)
            return


def _divide_batches(a, batch_size):
    for i in range(0, len(a), batch_size):
        yield a[i: i + batch_size]


def _setup_folder(output_folder):
    os.makedirs(os.path.join(output_folder, "img"), exist_ok=True)


def batch_img_generate(args):
    input_files, output_folder, styles, degradations, template, resolution = args
    generator = AnalogDocumentGeneration(
        styles=styles, degradations=degradations, resolution=resolution
    )
    for file in input_files:
        generator.generate_img(file, template, target_folder=output_folder)


def _set_batch_generate_args(
    file_batches, output_folder, styles, degradations, template, resolution
):
    return list(
        map(
            lambda batch: (
                batch,
                output_folder,
                styles,
                degradations,
                template,
                resolution,
            ),
            file_batches,
        )
    )


def generate_dataset_multiprocess(
    input_text_files,
    output_folder,
    styles,
    degradations,
    template,
    resolution=300,
    batch_size=25,
):
    _setup_folder(output_folder)
    print(f"Storing generated images in {output_folder}")

    batches = list(_divide_batches(input_text_files, batch_size))
    print(
        f"Splitting {len(input_text_files)} documents into {len(batches)} batches with size {batch_size}"
    )

    batch_img_generate_args = _set_batch_generate_args(
        batches, output_folder, styles, degradations, template, resolution
    )

    # Default to the number of processors on the machine
    start_time = timeit.default_timer()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        batch_iterator = executor.map(batch_img_generate, batch_img_generate_args)
        for _ in tqdm(
            batch_iterator, total=len(batch_img_generate_args)
        ):  # wrapping tqdm for progress report
            pass
    elapsed = timeit.default_timer() - start_time
    print(f"Time to generate {len(input_text_files)} documents: {elapsed:.3f} sec")
