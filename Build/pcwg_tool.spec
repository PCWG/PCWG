# -*- mode: python -*-

block_cipher = None


a = Analysis(['D:\\Git\\PCWG\\pcwg_tool.py'],
             pathex=['D:\\GIT\\PCWG\\Build'],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=block_cipher)
pyz = PYZ(a.pure,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='pcwg_tool.exe',
          debug=False,
          strip=None,
          upx=True,
          console=True )
