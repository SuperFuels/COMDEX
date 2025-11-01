importos

# ✅ DNA Switch
frombackend.modules.dna.dna_switchimportDNA_SWITCH
DNA_SWITCH.register(__file__)# Allow tracking + upgrades to this file

ROOT_DIR='backend'
OLD_IMPORT_PREFIX='modules'
NEW_IMPORT_PREFIX='backend.modules'

deffix_imports_in_file(filepath):
    withopen(filepath,'r',encoding='utf-8')asf:
        content=f.read()

new_content=content

# Replace "from modules." with "from backend.modules."
new_content=new_content.replace(f'from {OLD_IMPORT_PREFIX}.',f'from {NEW_IMPORT_PREFIX}.')

# Replace "import modules." with "import backend.modules."
new_content=new_content.replace(f'import {OLD_IMPORT_PREFIX}.',f'import {NEW_IMPORT_PREFIX}.')

ifnew_content!=content:
        withopen(filepath,'w',encoding='utf-8')asf:
            f.write(new_content)
print(f'Fixed imports in: {filepath}')

defmain():
    forsubdir,_,filesinos.walk(ROOT_DIR):
        forfileinfiles:
            iffile.endswith('.py'):
                filepath=os.path.join(subdir,file)
fix_imports_in_file(filepath)

if__name__=='__main__':
    main()