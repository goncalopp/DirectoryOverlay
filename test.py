BASE_DIR=   "test_base"
CUSTOM_DIR= "test_custom"

import random
import string
from os import mkdir, chdir, getcwd
from os.path import join, exists
from shutil import rmtree

import subprocess

from dir_overlay import DirectoryOverlay, DirectoryMerger

def random_filename():
    n=1
    return ''.join(random.choice(string.lowercase[:15]) for i in xrange(n))

def random_dirname():
    n=1
    return ''.join(random.choice(string.lowercase[15:]) for i in xrange(n))

def random_content():
    n=10
    return ''.join(random.choice(string.lowercase) for i in xrange(n))


def create_random_files_and_folders(directory, depth=3):
    if depth<0:
        return
    n_files= random.randint(0,30)
    n_dirs=  random.randint(0,5)
    files= [random_filename() for x in range(n_files)]
    dirs=  [random_dirname() for x in range(n_dirs)]
    for f in files:
        open(join(directory, f),'wb').write( random_content() )
    for d in dirs:
        d= join( directory, d)
        if not exists(d):
            mkdir(d)
            create_random_files_and_folders( d, depth= depth-1)

def file_hashes( directory ):
    old_cwd= getcwd()
    chdir( directory )
    '''generates hashes of all files inside directory (including subdirectories)'''
    out= subprocess.check_output( "find . -type f | xargs md5sum", shell=True)
    d= dict( (reversed(line.split()) for line in out.splitlines()) )  #dictionary of file:hash
    chdir( old_cwd )
    return d



#--------------------------

def setup():
    try:
        rmtree(BASE_DIR)
    except OSError:
        pass
    try:
        rmtree(CUSTOM_DIR)
    except OSError:
        pass
    mkdir(BASE_DIR)
    mkdir(CUSTOM_DIR)
    create_random_files_and_folders(BASE_DIR)
    create_random_files_and_folders(CUSTOM_DIR)

def test(direction):
    setup()
    destination= BASE_DIR if direction==DirectoryOverlay.TOBASE else CUSTOM_DIR
    overlay= DirectoryOverlay( BASE_DIR,  CUSTOM_DIR, ".", direction )
    overlay.clean()
    
    base_files=     file_hashes(BASE_DIR)
    custom_files=   file_hashes(CUSTOM_DIR)
    original_files= base_files if direction==DirectoryOverlay.TOBASE else custom_files
    overlay.apply()
    applied_files=  file_hashes(destination)
    overlay.clean()
    leftover_files= file_hashes(destination)
    
    base_filenames= set(base_files.keys())
    custom_filenames= set(custom_files.keys())
    all_filenames= base_filenames|custom_filenames

    print "testing files: {} on base, {} on custom, {} common".format(len(base_filenames), len(custom_filenames), len(base_filenames&custom_filenames))
    
    for fn in all_filenames:
        assert fn in applied_files                          #all base and custom files are there after applying...
        if fn in custom_files:
            assert applied_files[fn]==custom_files[fn]      #...and have the custom content if the custom file exists...
        else:
            assert applied_files[fn]==base_files[fn]        #...or the base content if it does not
    
    added_files= set(applied_files.keys())-set(all_filenames)                   #there are no files that weren't in either BASE or CUSTOM...
    assert all([ f.endswith(DirectoryMerger.BACKUP_EXT) for f in added_files ]) #...other than backup files
    
    
    
    assert original_files==leftover_files #after clean, we have the same files and  same content as originally
    

test(DirectoryOverlay.TOCUSTOM)
test(DirectoryOverlay.TOBASE)
print "all tests completed successfully"
