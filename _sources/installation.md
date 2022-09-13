# Installation

Genalog is supported across Windows, Mac and Linux on Python 3.6+. However there are *additional* installation steps for Windows and Mac users.


````{tab} pip
```sh
pip install genalog
```
````
````{tab} source
```sh
git clone https://github.com/microsoft/genalog.git && cd genalog && pip install -e .
```
````

## Extra Steps for Windows & Mac Users

We have a dependency on [`Weasyprint`](https://weasyprint.readthedocs.io/en/stable/install.html) for image generation, which in turn has non-python dependencies including `Pango`, `cairo` and `GDK-PixBuf` that need to be installed separately.

So far, `Pango`, `cairo` and `GDK-PixBuf` libraries are available in `Ubuntu-18.04` and later by default.

If you are running on Windows, MacOS, or other Linux distributions, please see [installation instructions from WeasyPrint](https://weasyprint.readthedocs.io/en/stable/install.html).

```{note}
If you encounter the errors like `no library called "libcairo-2" was found`, this is probably due to the three extra dependencies missing.
```

