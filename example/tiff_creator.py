

from PIL import Image
from PIL import TiffImagePlugin
import os

class TiffConverter():

    def convert_doc(target_directory, output_directory):
        for file in os.listdir(target_directory): 
            if file.endswith('.png'):
                path = os.path.join(target_directory, file)
                img = Image.open(path)
                name = file.split('.png')[0]
                img.save(output_directory + '/' + name + '.tiff', compression = 'tiff_lzw')


    def merge_tiffs(file_path, output_path, preffix = None):
            for tiff_in in os.listdir(file_path): 
                    name = tiff_in.split('.tiff')[0]
            with TiffImagePlugin.AppendingTiffWriter(output_path + '/' + name + '.tiff', True) as tf:        
                for tiff_in in os.listdir(file_path): 
                    im= Image.open(file_path+'/'+tiff_in)
                    im.save(tf,  compression = 'tiff_lzw')
                    tf.newFrame()
                    im.close() 

#TiffConverter.convert_doc(target_directory = 'example/generated_imgs', output_directory = 'example/converted_imgs')

TiffConverter.merge_tiffs('example/converted_imgs', 'example/multipage_tiffs')