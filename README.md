enctempfile
===========

`enctempfile` allows you to transparently encrypt temporary files. These files
are buffered in memory and broken down into blocks, and each individual block
is written to a temporary file and encrypted using
[Fernet](https://cryptography.io/en/latest/fernet/) encryption, with temporary
keys unique to each block.

Usage
=====

```!python
import enctempfile

with enctempfile.TemporaryFile() as fp:

    fp.write(b"hello")
    fp.flush()

    fp.seek(0)

    print(fp.read())
```

All temporary files are currently mode wb+, text mode is not supported. Block
size can be specified to the constructor using the `block_size` argument.
