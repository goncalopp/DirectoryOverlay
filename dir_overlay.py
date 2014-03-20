#edit these variables to point to the correct paths
BASE_DIR= "../base"
APPLY_DIR="custom"
STATE_FILE= ".base_merger.state"    #clean or applied state
LIST_FILE= ".base_merger.list"      #list of files that were copied


#-----end of user editable variables. Only real developers from this point on please :)


USAGE=  ("Usage: \n"
        "./dir_overlay.py  clean|apply \n"
        "\n"
        "The purpose of this script is to 'overlay' two directories, by reversibly copying the contents of one directory to the other. \n"
        "We define two directories (BASE_DIR and APPLY_DIR) and two operations (APPLY and CLEAN). \n"
        "APPLY copies the contents of BASE_DIR to APPLY_DIR. It doesn't copy any files that already exist on the destination, allowing you to put files on APPLY_DIR that are a 'customized version' of those on BASE_DIR. \n"
        "CLEAN indiscriminately removes any files that were created by APPLY. \n"
        "\n"
        "The script relies on relative paths, so you need a good CWD when you launch it (from a terminal, preferably...) \n"
        "Two state files are kept on the CWD - please don't delete them. \n"
        )
        

from os import remove, listdir, mkdir
from os.path import isdir, isfile, join, exists
from shutil import copyfile, rmtree

import logging
logging.basicConfig(level=logging.DEBUG, format= '%(message)s')



#----------------This section has pure classes and functions-----------------------------------------------


class StateFile:
    CLEAN, APPLIED= "clean", "applied"
    STATES= (CLEAN, APPLIED)
    
    def __init__(self, filename):
        self.filename= filename
        self.state= self._read_state()
    
    def _read_state(self):
        if not exists(STATE_FILE):
            self.set_state(self.CLEAN)
            return self.CLEAN
        state= open(STATE_FILE,'rb').read()
        for x in self.STATES:
            if state==x:
                return state
        raise Exception("Cannot read state from state file: "+state)

    def set_state(self, state):
        assert state in self.STATES
        f=open(STATE_FILE, 'wb')
        f.write(state)
        f.close()
        self.state= state



def recursive_directory_merge( from_dir, to_dir ):
    logging.debug("processing directory:".ljust(25)+from_dir+", "+to_dir)
    copied_files, copied_dirs= [], []
    relative_listing= listdir(from_dir)  #all files and dirs, with relative paths
    absolute_ft_listing= [(join(from_dir, x),join(to_dir, x)) for x in relative_listing] #(from,to) pairs, with absolute paths
    absolute_ft_files= [x for x in absolute_ft_listing if isfile(x[0])] #(from,to) pairs of files, with absolute paths
    absolute_ft_dirs=  [x for x in absolute_ft_listing if isdir(x[0])]  #(from,to) pairs of directories, with absolute paths
    for x in absolute_ft_files:
        ff,tf= x #from file, to file
        if exists(tf):
            continue    #ignore existing files
        logging.debug("copying file:".ljust(27)+ff)
        try:
            copyfile(ff, tf)
            copied_files.append( tf )
        except Exception as e:
            logging.error( str(e) )
    for x in absolute_ft_dirs:
        fd,td= x #from dir, to dir
        try:
            if not exists(td):
                mkdir(td)
                copied_dirs.append( td )    #copied_dirs do not contain already existent directories on to_dir - so that we don't delete them on a clean
            rcd, rcf= recursive_directory_merge( fd, td )
            copied_files.extend( rcf )
            copied_dirs.extend( rcd )
        except Exception as e:
            logging.error( str(e) )
    return copied_dirs, copied_files

def remove_changes(changes_list):
    '''simply delete all files and dirs on the list'''
    for x in changes_list:
        if isdir(x):
            logging.debug("removing directory: ".ljust(20)+x)
            rmtree(x)
        elif isfile(x):
            logging.debug("removing file: ".ljust(20)+x)
            remove(x)
        else:
            logging.warning("Cannot clean "+x)



#--This section has global-using and exit()ing functions,  and keeps external state------------------------------


s= StateFile(STATE_FILE)

def clean():
    if s.state==StateFile.CLEAN:
        logging.info("Already clean")
        exit(0)
    else:
        l= open(LIST_FILE, 'r').read().splitlines()
        remove_changes(l)
        s.set_state( StateFile.CLEAN )
        logging.info("Cleaned successfully")

def apply():
    if s.state==StateFile.APPLIED:
        logging.warning("Already applied. If you want to apply again, you need to clean first")
        exit(2)
    else:
        cd,cf= recursive_directory_merge( BASE_DIR, APPLY_DIR )
        remove_list= cf+list(reversed(cd)) #files first! otherwise we would remove directories, and THEN remove files on THOSE directories D: We need to reverse cd, to delete deeper directories first
        l= open(LIST_FILE, 'w').write("\n".join(remove_list)) 
        s.set_state( StateFile.APPLIED )
        logging.info("Applied successfully")
        
if __name__=="__main__":
    import sys
    operations= {"clean":clean, "apply":apply}
    op= sys.argv[-1]
    if len(sys.argv)<2 or not op in operations:
        print USAGE
        exit(1)
    if not isdir(BASE_DIR)or not isdir(APPLY_DIR):
        logging.critical("There is a problem with your directories (did you define the BASE_DIR and APPLY_DIR variables?)")
        exit(3)
    operations[op]()
