from genalog.text.label_generator import LabelGenerator, generate_labels
import genalog.text.label_generator
import os

def test_label_generator(tmpdir):
    genalog.text.label_generator.label_generator = LabelGenerator.create_from_env_var()
    generate_labels("tests/text/data/label_generator/text", tmpdir)
    assert open(f"{tmpdir}/0.txt").read() == open("tests/text/data/label_generator/labels/0.tsv").read()
    assert open(f"{tmpdir}/1.txt").read() == open("tests/text/data/label_generator/labels/1.tsv").read()
    assert open(f"{tmpdir}/11.txt").read() == open("tests/text/data/label_generator/labels/11.tsv").read()