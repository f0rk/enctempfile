import hashlib
import io
import random

import enctempfile


def test_basic():

    with enctempfile.TemporaryFile() as fp:

        fp.write(b"hello")
        fp.flush()

        fp.seek(0)

        data = fp.read()

        assert data == b"hello"

        fp.seek(0)

        b1 = fp.read(1)
        b2 = fp.read(1)
        b3 = fp.read(1)
        b4 = fp.read(1)
        b5 = fp.read(1)
        b6 = fp.read(1)

        assert b1 == b"h"
        assert b2 == b"e"
        assert b3 == b"l"
        assert b4 == b"l"
        assert b5 == b"o"
        assert b6 == b""


def test_random():

    random.seed(0)

    with enctempfile.TemporaryFile(block_size=5000) as fp:

        in_buffer = io.BytesIO()

        in_hash = hashlib.md5()

        for _ in range(1000):

            bytes_to_write = random.randint(1000, 10000)

            for _ in range(bytes_to_write):
                byte = bytes([random.randint(32, 126)])
                fp.write(byte)
                in_buffer.write(byte)

                in_hash.update(byte)

        out_hash = hashlib.md5()

        fp.seek(0)

        out_buffer = io.BytesIO()

        for _ in range(1000):

            bytes_to_read = random.randint(1000, 10000)

            bytes_read = fp.read(bytes_to_read)
            out_hash.update(bytes_read)
            out_buffer.write(bytes_read)

        remainder = fp.read()

        out_hash.update(remainder)
        out_buffer.write(remainder)

        assert in_hash.hexdigest() == out_hash.hexdigest()
        assert in_buffer.getvalue() == out_buffer.getvalue()


# there was a bug where reading from an otherwise untouched file would hang
# forever
def test_empty():

     with enctempfile.TemporaryFile(block_size=5000) as fp:
         data = fp.read()

         assert data == b""
