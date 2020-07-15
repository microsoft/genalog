import urllib.request
import os
import io
import tarfile
import stat

def get_azcopy(working_directory):
    azcopy_location = working_directory + '/bin/azcopy'
    if not os.path.isfile(azcopy_location):
        try:
            azcopy_dir = os.path.dirname(azcopy_location)
            if not os.path.exists(azcopy_dir):
                os.makedirs(azcopy_dir)
 
            file_url = 'https://azcopyvnext.azureedge.net/release20191212/azcopy_linux_amd64_10.3.3.tar.gz'
 
            req = urllib.request.urlopen(file_url)
 
            compressed_file = io.BytesIO(req.read())
 
            with tarfile.open(fileobj=compressed_file, mode="r:gz") as tar:
                for tarinfo in tar:
                    if tarinfo.isfile() and tarinfo.name.endswith('azcopy'):
                        with open(azcopy_location, 'wb') as f:
                            f.write(tar.extractfile(tarinfo).read())
 
            os.chmod(azcopy_location, os.stat(azcopy_location).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
 
        except Exception as ex:
            raise ex
 
    return azcopy_location