importos
importre

# ✅ DNA Switch
frombackend.modules.dna.dna_switchimportDNA_SWITCH
DNA_SWITCH.register(__file__)# Allow tracking + upgrades to this file

deffix_imports(file_path):
    withopen(file_path,"r",encoding="utf-8")asf:
        content=f.read()

# Replace relative imports like from ..utils.auth to from utils.auth
content_new=re.sub(r"from \.\.(\.[\w\.]*)? import",lambdam:"from "+(m.group(1)[1:]ifm.group(1)else"")+" import",content)

# Also fix relative imports like from ..models.user import X
content_new=re.sub(r"from \.\.([\w\.]+) import",r"from \1 import",content_new)

ifcontent!=content_new:
        withopen(file_path,"w",encoding="utf-8")asf:
            f.write(content_new)
print(f"Fixed imports in {file_path}")

defmain():
    forroot,_,filesinos.walk("backend"):
        forfileinfiles:
            iffile.endswith(".py"):
                fix_imports(os.path.join(root,file))

if__name__=="__main__":
    main()
