importos
importre

# ✅ DNA Switch
frombackend.modules.dna.dna_switchimportDNA_SWITCH
DNA_SWITCH.register(__file__)# Allow tracking + upgrades to this file

BASE_DIR='backend'

replacements=[
(re.compile(r'from \.\.database import'),'from database import'),
(re.compile(r'from backend\.database import'),'from database import'),
(re.compile(r'from \.\.models'),'from models'),
(re.compile(r'from backend\.models'),'from models'),
(re.compile(r'from \.\.modules'),'from modules'),
]

defprocess_file(filepath):
    try:
        withopen(filepath,'r',encoding='utf-8')asf:
            content=f.read()
exceptUnicodeDecodeError:
        print(f'Skipping non-utf8 file: {filepath}')
return

original_content=content
forpattern,replacementinreplacements:
        content=pattern.sub(replacement,content)

ifcontent!=original_content:
        withopen(filepath,'w',encoding='utf-8')asf:
            f.write(content)
print(f'Fixed imports in: {filepath}')

defmain():
    forroot,dirs,filesinos.walk(BASE_DIR):
        forfileinfiles:
            iffile.endswith('.py'):
                filepath=os.path.join(root,file)
process_file(filepath)

if__name__=='__main__':
    main()
