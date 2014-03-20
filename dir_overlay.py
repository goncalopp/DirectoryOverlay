#edit these variables to point to the correct paths
#BASE_DIR= "../base"
#CUSTOM_DIR="custom"
#DIRECTION= "TOBASE"                               #TOBASE or TOCUSTOM
#STATE_DIR="."


#-----end of user editable variables. Only real developers from this point on please :)


USAGE=  ("Usage: \n"
        "./dir_overlay.py  clean|apply \n"
        "\n"
        "Let us define two directories (BASE_DIR and CUSTOM_DIR) and two operations (APPLY and CLEAN). \n"
        "We also define DIRECTION as being either TOBASE or TOCUSTOM. \n"
        "The purpose of this script is to 'overlay' two directories, by reversibly copying the contents of one directory to the other. It allows you to put files on CUSTOM_DIR that are a 'customized version' of those on BASE_DIR\n"
        "If DIRECTION is TOCUSTOM: \n"
        "    APPLY copies the contents of BASE_DIR to CUSTOM_DIR. It doesn't copy any files that already exist on the destination. \n"
        "    CLEAN indiscriminately removes any files that were created by APPLY. IT DOES NOT CHECK FOR CHANGES IN THOSE FILES\n"
        "\n"
        "If DIRECTION is TOBASE: \n"
        "    APPLY copies the contents of CUSTOM_DIR to BASE_DIR. Files that already exist on the destination are backed up and replaced. \n"
        "    CLEAN removes any files that were created by APPLY, and restores the backups if they already existed. \n"
        "\n"
        "The script relies on relative paths, so you need a good CWD when you launch it (from a terminal, preferably...) \n"
        "Two state files are kept on the CWD - please don't delete them. \n"
        )
        

from os import remove, listdir, mkdir
from os.path import isdir, isfile, join, exists, normpath
from shutil import copyfile, rmtree, move
from functools import partial

import logging
logging.basicConfig(level=logging.INFO, format= '%(message)s')



#----------------This section has pure classes and functions-----------------------------------------------


class StateFile( object ):
    '''tracks state (CLEAN or APPLIED), using a file'''
    CLEAN, APPLIED= "clean", "applied"
    STATES= (CLEAN, APPLIED)
    
    def __init__(self, filename):
        self.filename= filename
        self.state= self._read_state()
    
    def _read_state(self):
        if not exists(self.filename):
            self.set_state(self.CLEAN)
            return self.CLEAN
        state= open(self.filename,'rb').read()
        for x in self.STATES:
            if state==x:
                return state
        raise Exception("Cannot read state from state file: "+state)

    def set_state(self, state):
        assert state in self.STATES
        f=open(self.filename, 'wb')
        f.write(state)
        f.close()
        self.state= state

class MergeHistory( object ):
    '''keeps a history of which files have been added/changed by a merge'''
    def __init__(self):
        self.changed= []  #files that were changed or did not exist OR directories that did not exist
    
    def add_file( self, f ):
        self.changed.append(f)
    
    def change_file( self, f ):
        self.changed.append(f)
    
    def add_dir( self, d):
        self.changed.append(d)
    
    def serialize_to_file( self, filename ):
        open(filename, 'w').write("\n".join(self.changed)) 
    
    @staticmethod
    def read_serialized_file( filename ):
        c= MergeHistory()
        c.changed= open(filename, 'r').read().splitlines()
        return c
        
class DirectoryMerger( object ):
    '''Exposes operations to merge two directories, and to revert the changes, through the use of a MergeHistory'''
    BACKUP_EXT='.dir_overlay_bak'
    def __init__(self, from_dir, to_dir, backup, replace):
        assert backup in (True, False)
        assert replace in (True, False)
        assert not (backup and not replace) #it doesn't make sense to backup and not replace...
        self.from_dir, self.to_dir= from_dir, to_dir
        self.backup=    backup
        self.replace=   replace
    
    def _backup_filename( self, f ):
        assert not f[-1] in ("/","\\")
        return f+self.BACKUP_EXT
    
    def _merge_file( self, from_file, to_file ):
        ex= exists(to_file)
        if ex and not isfile(to_file):
            raise Exception("File on origin has the same name as a non-file on destination: "+to_file)
        if ex and self.backup:
            move( to_file, self._backup_filename( to_file ) )
        if self.replace or not ex:
            logging.debug("copying  file:".ljust(27)+from_file)
            copyfile(from_file, to_file)
            if ex:
                self.changes.change_file( to_file )
            else:
                self.changes.add_file( to_file )
        else:
            logging.debug("ignoring file:".ljust(27)+from_file)
            return False

    def _merge_dir( self, from_dir, to_dir ):
        logging.debug("processing directory:".ljust(25)+from_dir+", "+to_dir)
        copied_files, copied_dirs= [], []
        relative_listing= listdir(from_dir)  #all files and dirs, with relative paths
        absolute_ft_listing= [(join(from_dir, x),join(to_dir, x)) for x in relative_listing] #(from,to) pairs, with absolute paths
        absolute_ft_files= [x for x in absolute_ft_listing if isfile(x[0])] #(from,to) pairs of files, with absolute paths
        absolute_ft_dirs=  [x for x in absolute_ft_listing if isdir(x[0])]  #(from,to) pairs of directories, with absolute paths
        for x in absolute_ft_dirs:
            fd,td= x #from dir, to dir
            try:
                dir_created= not exists(td)
                if dir_created:
                    mkdir(td)
                if not dir_created:
                    if not isdir(td):
                        raise Exception("Directory on origin has same name as a non-directory on destination: "+td)
                self._merge_dir( fd, td )
                if dir_created:     #copied_dirs do not contain already existent directories on to_dir - so that we don't delete them on a clean
                    self.changes.add_dir( td )    
            except Exception as e:
                logging.error( str(e) )
        for x in absolute_ft_files:
            ff,tf= x #from file, to file
            try:
                self._merge_file( ff, tf )
            except Exception as e:
                logging.error( str(e) )

    def merge( self ):
        self.changes= MergeHistory()
        self._merge_dir( self.from_dir, self.to_dir) 
        return self.changes

    def remove_changes(self, changes):
        '''delete all files and dirs on the list, and restores backups if existent'''
        assert isinstance(changes, MergeHistory)
        for x in changes.changed:
            if isdir(x):
                logging.debug("removing directory: ".ljust(20)+x)
                rmtree(x)
            elif isfile(x):
                logging.debug("removing file: ".ljust(20)+x)
                remove(x)
                if exists( self._backup_filename(x) ):
                    logging.debug("restoring file: ".ljust(20)+x)
                    move( self._backup_filename(x), x )
            else:
                logging.warning("Cannot clean "+x)
    
class DirectoryOverlay( object ):
    '''Uses a StateFile and a DirectoryMerger'''
    TOBASE, TOCUSTOM=   "tobase", "tocustom"
    DIRECTIONS=         (TOBASE, TOCUSTOM)
    STATE_FILE=         ".base_merger.state"    #clean or applied state
    CHANGES_FILE=       ".base_merger.list"      #list of files that were copied
    class AlreadyApplied( Exception ):
        pass
    def __init__(self, base_dir, custom_dir, state_dir, direction):
        assert direction in self.DIRECTIONS
        from_dir= base_dir if direction==self.TOCUSTOM else custom_dir
        to_dir=   base_dir if direction==self.TOBASE else custom_dir
        replace=  direction==self.TOBASE
        backup=   direction==self.TOBASE
        self.statefile=     StateFile(join(state_dir, self.STATE_FILE))
        self.merger=        DirectoryMerger( from_dir, to_dir, backup, replace )
        self.state_dir=     state_dir
    
    def _changes_file( self ):
        return join( self.state_dir, self.CHANGES_FILE)
    
    def clean( self ):
        if self.statefile.state==StateFile.CLEAN:
            logging.info("Already clean")
        else:
            changes= MergeHistory.read_serialized_file( self._changes_file() )
            self.merger.remove_changes( changes )
            self.statefile.set_state( StateFile.CLEAN )
            logging.info("Cleaned successfully")
    
    def _apply(self):
        if self.statefile.state==StateFile.APPLIED:
            logging.warning("Already applied. If you want to apply again, you need to clean first")
            raise self.AlreadyApplied
        changes= self.merger.merge()
        changes.serialize_to_file( self._changes_file() )
        self.statefile.set_state( StateFile.APPLIED )
        logging.info("Applied successfully")
        
    def apply(self, allow_repeated=False):
        if self.statefile.state==StateFile.APPLIED and allow_repeated:
            self.merger.clean()
        self._apply()

        
#--This section has global-using and exit()ing functions,  and keeps external state------------------------------

overlay= None #DirectoryOverlay( BASE_DIR, CUSTOM_DIR, STATE_DIR, DIRECTION )
    
def clean():
    overlay.clean()

def apply():
    overlay.apply(allow_repeated=False)

def reapply():
    overlay.apply(allow_repeated=True)

        
if __name__=="__main__":
    import sys
    operations= {"clean":clean, "apply":apply, "reapply":reapply}
    op= sys.argv[-1]
    if len(sys.argv)<2 or not op in operations:
        print USAGE
        exit(1)
    if not isdir(BASE_DIR) or not isdir(CUSTOM_DIR):
        logging.critical("There is a problem with your directories (did you define the BASE_DIR and CUSTOM_DIR variables?)")
        exit(2)
    try:
        operations[op]()
    except DirectoryOverlay.AlreadyApplied:
        exit(50)
