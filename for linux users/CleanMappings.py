from pathlib import Path
def transformMappings():
    obf = Path("./filesMappings/classes-obf.txt")
    deobf = Path("./filesMappings/classes-deobf.txt")
    with open(deobf,"r+") as d, open(obf,"r+") as o:
        temp=d.readlines()
        tempo=o.readlines()
        d.seek(0)
        o.seek(0)
        for e, el in zip(temp, tempo):
            if "$" not in e:
                d.write(e)
                o.write(el)
        d.truncate()
        o.truncate()


transformMappings()