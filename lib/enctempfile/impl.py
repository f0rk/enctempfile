import io
import os
import tempfile

from cryptography.fernet import Fernet


class Block(object):

    def __init__(self, block_size):
        self.block_size = block_size
        self.key = Fernet.generate_key()
        self.buffer = None
        self.fp = None

    def _load_buffer_from_fp(self):
        if self.fp is None:
            return

        self.fp.seek(0)
        self.buffer.seek(0)
        self.buffer.truncate()

        encrypted = self.fp.read()
        decrypter = Fernet(self.key)
        decrypted = decrypter.decrypt(encrypted)

        self.buffer.write(decrypted)
        self.buffer.seek(0)

    def write(self, *a, **kw):
        if self.buffer is None:
            self.buffer = io.BytesIO()
            self._load_buffer_from_fp()

        self.buffer.write(*a, **kw)

        current_position = self.buffer.tell()

        self.buffer.seek(0, os.SEEK_END)

        if self.buffer.tell() > self.block_size:
            raise Exception(
                "Implementation Error: caller wrote more than block_size {} "
                "bytes to internal buffer"
                .format(self.block_size)
            )

        self.buffer.seek(current_position)

    def seek(self, *a, **kw):
        if self.buffer is None:
            self.buffer = io.BytesIO()
            self._load_buffer_from_fp()
        return self.buffer.seek(*a, **kw)

    def read(self, *a, **kw):
        if self.buffer is None:
            self.buffer = io.BytesIO()
            self._load_buffer_from_fp()
        return self.buffer.read(*a, **kw)

    def tell(self, *a, **kw):
        if self.buffer is None:
            self.buffer = io.BytesIO()
            self._load_buffer_from_fp()
        return self.buffer.tell(*a, **kw)

    def flush(self):

        if self.buffer is None:
            return 0

        encrypter = Fernet(self.key)
        encrypted = encrypter.encrypt(self.buffer.getvalue())

        if self.fp is None:
            self.fp = tempfile.TemporaryFile()
        else:
            self.fp.seek(0)
            self.fp.truncate()

        self.fp.write(encrypted)

        self.buffer.seek(0)
        self.buffer.truncate()
        self.buffer = None

        return len(encrypted)

    def truncate(self, *a, **kw):
        if self.buffer is None:
            self.buffer = io.BytesIO()
            self._load_buffer_from_fp()
        return self.buffer.truncate(*a, **kw)

    def close(self):
        if self.fp is not None:
            self.fp.close()

        self.key = None
        self.buffer = None
        self.fp = None


DEFAULT_BLOCK_SIZE = 1024 * 1024 * 16


class TemporaryFile(object):

    def __init__(self, block_size=DEFAULT_BLOCK_SIZE):
        self.blocks = {}
        self.block_size = block_size
        self.position = 0
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def _get_block_number(self, position):
        return position // self.block_size

    def _get_block(self, block_number):
        return self.blocks.get(block_number)

    def _create_block(self, block_number):
        block = Block(self.block_size)

        if block_number in self.blocks:
            raise Exception(
                "Block already exists for block_number {}"
                .format(block_number)
            )

        self.blocks[block_number] = block

        return block

    def _get_max_block_number(self):
        max_block_number = None
        for block_number in self.blocks.keys():
            if max_block_number is None or block_number > max_block_number:
                max_block_number = block_number

        return max_block_number

    def _get_block_local_position(self, block_number):
        block_local_position = (
            self.position
            - (
                block_number
                * self.block_size
            )
        )

        return block_local_position

    def write(self, b):

        block_number = self._get_block_number(self.position)

        current_block = self._get_block(block_number)
        if current_block is None:
            current_block = self._create_block(block_number)

        # seek the current block's buffer to our position, accounting for the
        # block number and offset
        block_local_position = self._get_block_local_position(block_number)
        current_block.seek(block_local_position)

        # split into two blocks
        if current_block.tell() + len(b) > self.block_size:
            first_chunk_len = self.block_size - current_block.tell()

            first_chunk = b[:first_chunk_len]
            second_chunk = b[first_chunk_len:]

            current_block.write(first_chunk)
            current_block.flush()

            self.position += len(first_chunk)

            self.write(second_chunk)
        else:
            current_block.write(b)
            self.position += len(b)

    def fileno(self):
        raise OSError("no fileno")

    def isatty(self):
        return False

    def readable(self):
        return True

    def close(self):
        for block in self.blocks.values():
            block.close()

        self.blocks = {}

        self.closed = True

    def flush(self):
        for block in self.blocks.values():
            block.flush()

    def tell(self):
        return self.position

    def seek(self, offset, whence=os.SEEK_SET):
        if whence == os.SEEK_SET:
            self.position = offset
        elif whence == os.SEEK_END:

            max_block_number = self._get_max_block_number()
            if max_block_number is None:
                return

            max_block = self.blocks[max_block_number]
            current_max_block_position = max_block.tell()

            max_block.seek(0, os.SEEK_END)
            max_block_size = max_block.tell()

            max_block.seek(current_max_block_position)

            full_size = (
                max_block_size
                + (
                    max_block_number
                    * self.block_size
                )
            )

            self.position = full_size - offset
        elif whence == os.SEEK_CUR:
            self.position = self.position + offset
        else:
            raise ValueError("Invalid value for whence {!r}".format(whence))

    def read(self, size=-1):

        ret_buffer = []

        while True:

            if size == 0:
                return b"".join(ret_buffer)

            block_number = self._get_block_number(self.position)

            current_block = self._get_block(block_number)
            if current_block is None:

                # if this is the last block, return nothing
                max_block_number = self._get_max_block_number()
                if max_block_number is None:
                    return b"".join(ret_buffer)

                if max_block_number == block_number:
                    return b"".join(ret_buffer)

                # assume entire content of this block is null bytes
                else:
                    block_local_position = self._get_block_local_position(block_number)
                    bytes_remaining = self.block_size - block_local_position

                    if size == -1:
                        to_return = bytes_remaining
                    else:
                        to_return = min(size, bytes_remaining)
                        size -= to_return

                    ret_buffer.append(b"\0" * to_return)

                    self.position += to_return

            else:

                block_local_position = self._get_block_local_position(block_number)
                current_block.seek(block_local_position)
                data = current_block.read(size)

                if len(data) == 0:
                    return b"".join(ret_buffer)

                size -= len(data)

                ret_buffer.append(data)

                self.position += len(data)

    def seekable(self):
        return True

    def truncate(self, size=None):
        current_position = self.position

        if size is not None:
            self.seek(self.size, os.SEEK_CUR)

        block_number = self._get_block_number(self.position)

        # remove every block larger than this number
        for local_block_number, local_block in self.blocks.items():
            if local_block_number > block_number:
                local_block.close()
                del self.blocks[local_block_number]

        # truncate this block as necessary
        current_block = self._get_block(block_number)
        if current_block is not None:
            block_local_position = self._get_block_local_position(block_number)
            current_block.seek(block_local_position)
            current_block.truncate()
            current_block.flush()

        self.seek(current_position)

    def writable(self):
        return True
