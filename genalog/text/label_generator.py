from enum import Enum
import json
import os
import logging
import argparse
import torch
import pandas as pd
from tqdm import tqdm
import multiprocessing
from nltk.tokenize import word_tokenize, sent_tokenize
from multiprocessing import Pool
from tatk.GeneralNER.general_ner import GeneralNERInterface
from tatk.GeneralNER.pipelines.mt_lstm_entity_extractor import MultiTaskLSTMEntityExtractor

DEFAULT_MODEL_ROOT_PATH = "/mnt/c/Users/dabanda/Downloads/entitygeneral/tatk"
DEFAULT_MODEL_VERSION = "1.0.0.1"
BATCH_SIZE = 50
BUFFER_SIZE = 100
WORKERS_PER_CPU = 2

label_generator = None

class LabelGenerator():
    @staticmethod
    def create_from_env_var(use_general_ner=False):
        model_root_path = os.environ.get("MODEL_ROOT_PATH", DEFAULT_MODEL_ROOT_PATH)
        model_version = os.environ.get("MODEL_VERSION", DEFAULT_MODEL_VERSION )
        return LabelGenerator(model_root_path, model_version, use_general_ner=use_general_ner)

    def __init__(self, model_root_path=DEFAULT_MODEL_ROOT_PATH, model_version=DEFAULT_MODEL_VERSION,use_general_ner=False):
        model_path = os.path.join(model_root_path, model_version )
        print("loading model:", model_path)
        self.use_general_ner = use_general_ner
        # if use_general_ner:
        self.general_ner = GeneralNERInterface(model_path = os.path.join(model_path, "final_model"), 
                        batch_size=500,
                        input_text_col='text', 
                        input_id_col='id', 
                        output_list = [0],
        )
        
    def run_ner_predict(self, doc_json):
        """Call the NER model to perform predictions on batches of docs

        Args:
            doc_json (dict): json dict of the doc with keys text and id.

        Returns:
            pandas.DataFrame: Pandas dataframe of the prediction result
        """
        with torch.no_grad():
            dataset = pd.DataFrame(doc_json)
            dataset = self.general_ner.sentence_splitter.tatk_transform(dataset) 
            dataset = self.general_ner.preprocessor.tatk_transform(dataset)
            dataset = self.general_ner.pipeline.predict(dataset)
            return dataset

    def run_predictor(self, doc_json): 
        tsv_collection = {}
        with torch.no_grad():
            for doc in doc_json:
                input_text = []
                sentences = sent_tokenize(doc["text"])
                for sentence in sentences:
                    if len(sentence.strip())>0:
                        tokens = word_tokenize(sentence)
                        # replace double single quotes and double back tick to a single double quote
                        # this happens after word_tokenize as it replaces quotes to `` and ''
                        tokens = [tok.replace('``', '"').replace("''", '"') for tok in tokens]
                        input_text.append(tokens)
                output = self.general_ner.pipeline.predictor._predict_single(input_text)
                iob_labels = output[0][0]
                tsv_string = ""
                for tokens_sent, labels_sent in zip(input_text, iob_labels):
                    for token, label in zip(tokens_sent, labels_sent):
                        tsv_string += f'{token}\t{label}\n'
                    tsv_string += '\n'

                tsv_collection[doc["id"]] =tsv_string
        return tsv_collection

    def get_labels_tsv_collection(self, doc_json):
        """Run prediction on a batch of json docs and get the labeled tsv

        Args:
            doc_json (list(dict)): json array of payload with keys id and text

        Returns:
            dict: dict of tsv content that has doc_id as key for the tsv string
        """
        prediction = self.run_ner_predict(doc_json)
        prediction_dict = self._group_by_id(prediction).to_dict()
        tsv_collection =  self._df_dict_to_tsv(prediction_dict, doc_json)
        return tsv_collection
    
    def _group_by_id(self, df):
        """Groups the resulting dataframe output of predict by the id value of the docs

        Args:
            df (pandas.DataFrame): dataframe of the prediction output
        """
        def update_offsets(row):
            sentence_offset = row["sentence_offset"]
            offsets = row["offset"]
            offest_list = map( lambda x: (x[0] + sentence_offset, x[1]+ sentence_offset), offsets)
            return list(offest_list)

        df = df.sort_values(by=["id", "sentence_offset"], ascending=(True,True))
        df = df[["id", "sentence", "iob_label_0", "sentence_offset", "offset"]]
        df["offset"] = df.apply(update_offsets, axis=1)
        df = df.groupby("id").agg({"sentence" : lambda x : " ".join(x), "iob_label_0": "sum", "offset": "sum"})
        return df

    def _df_dict_to_tsv(self, df_dict, doc_json, doc_seperator=None):
        df_dict["original_sentences"] = {}
        for doc in doc_json:
            df_dict["original_sentences"][doc["id"]] = doc["text"]

        ids = df_dict["sentence"].keys()
        tsv_collection = {}
        for doc_id in ids:
            tsv_string = ""
            sentence = df_dict["original_sentences"][doc_id]
            offsets = df_dict["offset"][doc_id]
            labels = df_dict["iob_label_0"][doc_id]
            for i, offset in enumerate(offsets):
                start, end = offset
                label = labels[i]
                token = sentence[start:end]
                tsv_string += f"{token}\t{label}\n"
                if token[-1] == ".":
                    tsv_string += "\n"
            if doc_seperator:
                tsv_collection[doc_id] = tsv_string + doc_seperator
            else:
                tsv_collection[doc_id] = tsv_string
        return tsv_collection

    def get_predictor(self, model_path, embedding_file_path, cuda_device=-1):
        input_text_col = 'text'
        input_id_col = 'id'
        preprocessed_col = 'preprocessed_text'
        offset_col = 'offset'
        iob_label_col = 'iob_label'
        standoff_col = 'standoff'
        sentence_col = 'sentence'
        sentence_offset_col = 'sentence_offset'
        sentence_standoff_col = 'sentence_standoff'
        probabilities_col = 'probabilities'
        emb_file = embedding_file_path
        mt_lstm_entity_extractor = MultiTaskLSTMEntityExtractor(input_text_col = input_text_col,
                                                            input_id_col = input_id_col,
                                                            preprocessed_col = preprocessed_col,
                                                            offset_col = offset_col,
                                                            iob_label_col = iob_label_col,
                                                            probabilities_col = probabilities_col,
                                                            standoff_col = standoff_col,
                                                            sentence_col = sentence_col,
                                                            sentence_offset_col = sentence_offset_col,
                                                            sentence_standoff_col = sentence_standoff_col,
                                                            cuda_device = cuda_device,
                                                            output_list = [0],
                                                            emb_file = emb_file
                                                         )
        ################ load model 
        print("============= Loading Model =============")
        mt_lstm_entity_extractor.load(model_path)

        return mt_lstm_entity_extractor.predictor


def generate_labels(input_dir, output_dir, batch_size=BATCH_SIZE, buffer_size=BUFFER_SIZE, use_multiprocessing=True):
    cpu_count = multiprocessing.cpu_count()
    n_workers = WORKERS_PER_CPU * cpu_count
    
    if use_multiprocessing:
        pool = Pool(n_workers) 

    job_args = []
    txt_files = os.listdir(input_dir)
    batch = []

    # count total number of lines:
    total_line_count = 0
    for fname in txt_files:
        total_line_count += sum(1 for _ in open(f"{input_dir}/{fname}", 'rb'))

    progress_bar = tqdm(total=total_line_count)
    def process_jobs(job_args):
        tsv_data = []
        if use_multiprocessing:
            for tsv_item in pool.imap_unordered(_label_worker, job_args, chunksize=n_workers):
                progress_bar.update(tsv_item["doc_count"])
                tsv_data.append(tsv_item)
        else:
            for tsv_item in map(_label_worker, job_args):
                progress_bar.update(tsv_item["doc_count"])
                tsv_data.append(tsv_item)
        write_batch(tsv_data, output_dir)

    for fname in txt_files:
        with open(f"{input_dir}/{fname}", encoding="utf8") as f:
            count = 0
            for line in f:
                if len(batch) < batch_size:
                    if line.strip():
                        batch.append(line)
                else:
                    minibatch = {
                        "filename": fname,
                        "position": count,
                        "txt": batch
                    }
                    job_args.append((input_dir, minibatch, output_dir))
                    count += 1
                    if line.strip():
                        batch = [line]
                    else:
                        batch = []

                    if len(job_args) > buffer_size:
                        process_jobs(job_args)
                        job_args = []
            if batch:
                # add last remaining batch
                minibatch = {
                    "filename": fname,
                    "position": count,
                    "txt": batch
                }
                job_args.append((input_dir, minibatch, output_dir))
                if len(job_args) > buffer_size:
                    process_jobs(job_args)
                    job_args = []
                batch = []

    if len(job_args) > 0:
        process_jobs(job_args)
        

def write_batch(tsv_data, output_dir):
    tsv_data = sorted(tsv_data, key = lambda x: x["position"])
    for item in tsv_data:
        fname = item["filename"]
        with open(f"{output_dir}/{os.path.splitext(fname)[0]}.txt", "ab") as out_file:
            for doc_id in range(item["doc_count"]):
                out_file.write(item[doc_id].encode("utf8"))

def _label_worker(args,overwite=False):
    _, batch, _  = args
    doc_json_batch = []
    txt_file_name = batch["filename"]
    position = batch["position"]
    for i, txt in enumerate(batch["txt"]):
        doc_id = i
        doc_json_batch.append({
            "id": doc_id ,
            "text" : txt
        })
    if label_generator.use_general_ner:
        tsv_collection = label_generator.get_labels_tsv_collection(doc_json_batch) 
    else:
        tsv_collection = label_generator.run_predictor(doc_json_batch)
    tsv_collection["filename"] = txt_file_name
    tsv_collection["doc_count"] = len(batch["txt"])
    tsv_collection["position"] = position
    return tsv_collection

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", help="input folder containing text files")
    parser.add_argument("output_dir", help="folder to place label tsv files")
    parser.add_argument("--use_multiprocessing", help="use multiprocessing", default=True, type=bool)
    parser.add_argument("--batch_size", default=BATCH_SIZE, help="batch size", type=int)
    parser.add_argument("--buffer_size", default=BUFFER_SIZE, help="buffer size that is used to hold the batches", type=int)
    args = parser.parse_args()
    label_generator = LabelGenerator.create_from_env_var()
    generate_labels(args.input_dir, args.output_dir, batch_size=args.batch_size, 
        use_multiprocessing=args.use_multiprocessing, buffer_size=args.buffer_size)
