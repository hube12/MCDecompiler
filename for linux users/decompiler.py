#!/usr/bin/python
from pathlib import Path
from shutil import copyfile,rmtree
import JDKcheck,subprocess,random,sys,os
checkJDK=True
removeBad=["summary.txt"]
import time

def copydir(source, dest):
    """Copy a directory structure overwriting existing files"""
    for root, dirs, files in os.walk(source):
        if not os.path.isdir(root):
            os.makedirs(root)
        for each_file in files:
            rel_path = root.replace(source, '').lstrip(os.sep)

            dest_path = os.path.join(dest, rel_path)
            if not os.path.isdir(dest_path):
                os.makedirs(dest_path)
            dest_path=os.path.join(dest_path, each_file)
            copyfile(os.path.join(root, each_file), dest_path)

def findjar():
    path=Path("./1.13.1.jar")
    if not path.exists():
        path=Path("~/AppData/Roaming/.minecraft/versions/1.13.1/1.13.1.jar").expanduser()
        if not path.exists():
            path=None
            print("No Jar found")
    if path:
        path=path.resolve()
    return path

def decompileJar():
    path=findjar()
    if path:
        cfr=Path("./lib/cfr_0_132.jar")
        if cfr.exists():
            cfr=cfr.resolve()
            #ok that part isnt necessary but i want cfr to work
            if checkJDK:
                path_to_jdk=Path(JDKcheck.main())
                if not path_to_jdk.exists():
                    path_to_jdk=None
                    print("Path to JDK is wrong af, put checkJDK=False in the import and relaunch if you are sure.")
                else:
                    path_to_jdk=path_to_jdk.resolve()
            
            subprocess.run(["java","-jar",cfr.__str__(),path.__str__(),"--outputdir","./temp","--caseinsensitivefs","true"])
            return True
        else:
            print("Missing a library: CFR")
    else:
        print("Missing a jar: 1.13.1.jar")
    return False

def applyFileMappings():
    obf=Path("./filesMappings/classes-obf.txt")
    deobf=Path("./filesMappings/classes-deobf.txt")
    mapping={}
    if obf.exists() and deobf.exists():

        #create the mapping dictionary for later application
        with open(deobf) as d,open(obf) as o:
            for e,el in zip(d,o):
                if "$" not in el:
                    mapping[el.strip("\n")]=e.strip("\n")

        #create the root node of the Tree
        src="src/"
        try:
            Path(src).mkdir()
        except FileExistsError:
            print("I saw you already have a src, you might not want to change things in it, shall we create a new src directory? y/n ")
            resp=input()
            if resp.lower() in ["y","yes","ofc","yeah","yea","ye","yep","alright"]:
                src="src"+str(random.getrandbits(128))+"/"
                Path(src).mkdir()
            else:
                print("Shall i overwrite everything? y/n")
                resp = input()
                if resp.lower() not in ["y", "yes", "ofc", "yeah", "yea", "ye", "yep", "alright"]:
                    sys.exit()

        #Apply the mappings and create the file Tree

        path_to_temp = Path("./temp")
        #remove some file generated by cfr
        for el in removeBad:
            if path_to_temp.joinpath(el).exists():
                path_to_temp.joinpath(el).unlink()

        for file in path_to_temp.iterdir():
            if file.is_file():
                nameObf=file.__str__().split("/")[1].split(".")[0] if file.__str__().split("/")[1].split(".")[1]=="java" else None
                nameDeObf=mapping[nameObf] if  nameObf in mapping else None
                if nameDeObf:
                    route="/".join(nameDeObf.split("/")[:-1])
                    try:
                        Path(src).joinpath(route).mkdir(parents=True)
                    except FileExistsError:
                        pass
                    destination=Path(src).joinpath(nameDeObf+".java")
                else:
                    print("I found one bad file: {}, it will be added at src/wtf/".format(file.__str__()))
                    try:
                        Path(src).joinpath("wtf").mkdir()
                    except FileExistsError:
                        pass
                    destination=Path(src).joinpath("wtf").joinpath(file.__str__().split("/")[1])
                source = Path(file)
                if destination.exists():
                    mode='wb'
                else:
                    mode="xb"
                with destination.open(mode=mode) as fid:
                    fid.write(source.read_bytes())
            else:

                copydir(file.__str__(),src.strip("/")+"/net")
        rmtree("temp/")
    else:
        print("Missing files mappings: obf and deobf")



if __name__=="__main__":
    t=time.time()
    print("Starting, might take a few seconds to minutes, depends of your potato")
    decompileJar()
    print("Decompilation completed, starting the file renaming")
    applyFileMappings()
    print("File Renaming, starting the class name renaming (wip for now)")
    print("Done in {}".format(time.time()-t))
    print("Your files will be in /src")
