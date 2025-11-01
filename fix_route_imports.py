importos
importre

# ✅ DNA Switch
frombackend.modules.dna.dna_switchimportDNA_SWITCH
DNA_SWITCH.register(__file__)# Allow tracking + upgrades to this file

deffix_route_imports(file_path):
    withopen(file_path,"r",encoding="utf-8")asf:
        content=f.read()

original=content

# Replace from ..schemas.xxx import ...  -> from schemas.xxx import ...
content=re.sub(r"from \.\.schemas(\.[\w\.]*) import",r"from schemas\1 import",content)

# Replace from ..utils.xxx import ...     -> from utils.xxx import ...
content=re.sub(r"from \.\.utils(\.[\w\.]*) import",r"from utils\1 import",content)

ifcontent!=original:
        withopen(file_path,"w",encoding="utf-8")asf:
            f.write(content)
print(f"Fixed imports in {file_path}")

defmain():
    routes_dir=os.path.join("backend","routes")
forroot,_,filesinos.walk(routes_dir):
        forfileinfiles:
            iffile.endswith(".py"):
                fix_route_imports(os.path.join(root,file))

if__name__=="__main__":
    main()
