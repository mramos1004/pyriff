#!/usr/bin/python2.4
# (C) Simon Drabble  2008
# This software is released under the Gnu General Public Licence v2.0.
# See http://www.gnu.org/licenses/old-licenses/gpl-2.0.html


__author__ = 'Simon Drabble <python-devel@thebigmachine.org>'


import sys
from StringIO import StringIO
import struct


class Struct(object):
  """Models a simple structure."""

  _types_ = {}
  _defaults_ = {}

  def __init__(self, *args, **kwargs):
    """Constructor.

    Args:
      args: sequence of parameter values used to initialise the structure.
      kwargs: dict of parameter values used to initialise the structure, plus
              other special keys:
                raw_data - str, such as might be read from a file.
                stream - any file-like object, must support read, seek,
                         and tell at a minimum. Supercedes raw_data.

    Each slot within the struct is initialised either in order from args, from
    keywords in kwargs, or via raw data in raw_data or stream.
    """
    raw_data = kwargs.pop('raw_data', None)
    stream = kwargs.pop('stream', None)

    if stream:
      my_type, size = struct.unpack('<4sI', stream.read(8))
      raw_data = stream.read(size)

    if raw_data:
      unpacked_data = list(self._Unpack(raw_data))
      for param in self.__slots__:
        setattr(self, param, unpacked_data.pop(0))

    else:
      for param in self.__slots__:
        var = kwargs.get(param, self._defaults_.get(param, None))
        if param in self._types_:
          if not isinstance(var, self._types_[param]):
            raise AttributeError('Parameter %s is of type %s, not %s' %
                               (param, type(var), self._types_[param]))
        setattr(self, param, var)

  def __str__(self):
    slist = map(lambda x: '\t%s=%s' % (x, getattr(self, x)), self.__slots__)
    return '\n'.join((self.ID, '\n'.join(map(str, slist))))

  def _Pack(self):
    """Packs the structure for storage/ transmission.

    Returns:
      str, the packed data.
    """
    params = map(lambda x: getattr(self, x), self.__slots__)
    return struct.pack(self._FORMAT, *params)

  def _Unpack(self, data):
    """Unpacks data into a sequence of params.
    
    Used when initialising from a stream or raw data.

    Args:
      data: str, raw bytes containing the packed struct data.

    Returns:
      tuple, each element is the value of an instance variable.

    Raises:
      struct.error, if the incoming data cannot be unpacked.
    """
    try:
      return struct.unpack(self._FORMAT, data)
    except struct.error, e:
      raise struct.error('Data of length %d could not be unpacked into'
                         ' size %s format %s' %
                         (len(data), struct.calcsize(self._FORMAT), self._FORMAT
                         ))

  def _GetLength(self):
    """Returns the length of self's packed data.

    Returns:
      int
    """
    return len(repr(self))
  length = property(_GetLength, None, None, None)


class Chunk(Struct):

  __slots__ = ()
  _FORMAT = ''

  def __repr__(self):
    data = self._Pack()
    length = len(data)
    if length % 2:
      data += '\0'
    return struct.pack('4sI%ds' % len(data), self.ID, length, data)


class LIST(Chunk, list):
  """Models a RIFF LIST Chunk."""

  _HEADER = 'LIST'
  _CLASSES = {}
  _CHUNKBASE = None

  def __init__(self, *args, **kwargs):
    """Constructor.

    Args:
      args: sequence of parameter values used to initialise the list.
      kwargs: dict of parameter values used to initialise the structure, plus
              other special keys:
                raw_data - str, such as might be read from a file.
                stream - any file-like object, must support read, seek,
                         and tell at a minimum. Superceded by raw_data.

    Each element within the list is initialised either in order from args,
    from keywords in kwargs, or via raw data in raw_data or stream.
    """
    stream = kwargs.pop('stream', None)
    raw_data = kwargs.pop('raw_data', None)
    if raw_data is not None:
      stream = StringIO(raw_data)

    if stream:
      if self._HEADER:
        stream.seek(len(self._HEADER), 1)
      list_size, list_type = struct.unpack('<I4s', stream.read(8))
      if list_type != self.ID:
        raise ValueError('%s is not a %s: ID=%s' %
                         (self._HEADER, self.ID, list_type))

      self.extend(self._UnpackStream(stream))

    else:
      for param in self.__slots__:
        var = kwargs.get(param, self._defaults_.get(param, None))
        if param in self._types_:
          if not isinstance(var, self._types_[param]):
            raise AttributeError('Parameter %s is of type %s, not %s' %
                               (param, type(var), self._types_[param]))
          if isinstance(None, self._types_[param]) and var is None:
            continue
        else:
          if var is None:
            continue
        self.append(var)

  def __str__(self):
    s = '%s\n\t%s\n%s' % (self._HEADER, self.ID, '\n'.join(map(str, self[:])))
    return s

  def __repr__(self):
    data = ''.join(map(repr, self[:]))
    return struct.pack('<4sI4s%ds' % len(data),
                       self._HEADER, len(data) + 4, self.ID, data)

  def __getattr__(self, key):
    try:
      return self[list(self.__slots__).index(key)]
    except ValueError, e:
      raise ValueError('Attribute %s not found in %s of %s' %
                       (key, self.__slots__, self.__class__))

  def append(self, item):
    if not (hasattr(item, 'ID') and hasattr(item, '_Pack')):
      raise AttributeError('append: Item %s<%s> is not a valid RIFF chunk' %
                           (item, item.__class__))
    list.append(self, item)

  def insert(self, pos, item):
    if not (hasattr(item, 'ID') and hasattr(item, '_Pack')):
      raise AttributeError('append: Item %s<%s> is not a valid RIFF chunk' %
                           (item, item.__class__))
    list.insert(pos, item)

  def extend(self, items):
    for item in items:
      self.append(item)

  def _Unpack(self, data):
    """Unpacks the data into separate values, one per element.

    Used when initialising from a stream or raw data.

    Args:
      data: str, raw bytes containing the packed struct data.

    Returns:
      iterable, each item is the value of an element.
    """
    return self._UnpackStream(StringIO(data))

  def _UnpackStream(self, stream):
    """Unpacks the stream data into separate values, one per element.

    Used when initialising from a stream or raw data.

    Args:
      stream: file-like, must support read, seek, and tell.

    Returns:
      iterable, each item is the value of an element.
    """
    cf = ChunkFactory(self, stream, datadict=self._CLASSES,
                      chunkbase=self._CHUNKBASE)
    return iter(cf)


class MultiRecordList(LIST):
  """Models a sequence of similar data structures that are not Chunks."""

  _HEADER = None

  def __init__(self, raw_data=None, stream=None):
    """Constructor.

    Args:
      raw_data: str, contains the binary struct data.
      stream: file-like, must support read, seek, and tell. Contains the binary
              struct data if raw_data is None. Superceded by raw_data.

    Exactly one of raw_data or stream must be present.
    """
    if raw_data:
      stream = StringIO(raw_data)

    while True:
      data = stream.read(struct.calcsize(self._RECORD_STRUCT._FORMAT))
      if not data:
        break
      obj = self._RECORD_STRUCT(raw_data=data)
      self.append(obj)

  def __repr__(self):
    data = ''.join(map(repr, self[:]))
    return struct.pack('<4s%ds' % len(data), self.ID, data)

  def __str__(self):
    data = ''.join(map(str, self[:]))
    return struct.pack('<6s%ds' % len(data), '<%s>' % self.ID, data)


class RIFF(LIST):
  """Models a RIFF form."""

  ID = 'RIFF'
  _HEADER = 'RIFF'

  def __init__(self, *args, **kwargs):
    """Constructor.

    Args:
      args: sequence of parameter values used to initialise the list.
      kwargs: dict of parameter values used to initialise the structure, plus
              other special keys:
                filename - str, the name of the RIFF file.
                stream - any file-like object, must support read, seek,
                         and tell at a minimum. Superceded by filename.

    """
    filename = kwargs.pop('filename', None)
    stream = kwargs.pop('stream', None)
    if filename:
      stream = open(filename)
    if stream:
      LIST.__init__(self, stream=stream)
    if filename:
      stream.close()
    if not (filename or stream):
      LIST.__init__(self, *args, **kwargs)

  def Save(self, filename):
    """Writes the RIFF data to a file.

    Args:
      filename: str, the name of the file to write.
    """
    f = open(filename, 'w')
    f.write(repr(self))
    f.close()


class ZeroPaddedString(Chunk):
  """Models a string with optional binary-zero padding."""

  def _Unpack(self, data):
    """Unpacks data into a sequence of params.
    
    Used when initialising from a stream or raw data.

    Args:
      data: str, raw bytes containing the packed struct data.

    Returns:
      tuple, each element is the value of an instance variable.
    """

    dlist = list(Chunk._Unpack(self, data))
    for index in self._STRINGS:
      dlist[index] = dlist[index].strip('\0')
    return tuple(dlist)


class ChunkFactory(list):
  """Automatic Chunk initialiser."""

  def __init__(self, caller, stream, datadict=None, chunkbase=False):
    """Constructor.

    Args:
      caller: object, the calling RIFF or LIST.
      stream: file-like, must support read, seek, and tell. Contains the raw
              chunk data.
      datadict: dict, {'chunk ID': class_object}.
      chunkbase: class, the base for chunk classes to be automatically created
                 for chunk IDs absent in datadict.
    """
    self._caller = caller
    self._stream = stream
    self._datadict = datadict
    self._chunkbase = chunkbase
    self._Read()

  def _Read(self):
    """Reads and initialises the chunks."""
    stream = self._stream

    while True:
      data = stream.read(8)
      if not data:
        break
      chunk_type, size = struct.unpack('<4sI', data)

      if chunk_type == 'LIST' or chunk_type == 'RIFF':
        list_type, = struct.unpack('4s', stream.read(4))
        # LIST-types don't have an explicit size
        # (the LIST itself does, of course, since that's a Chunk)
        # the size needs to apply to the next-read chunk
        chunk_type = list_type

        # Rewind the 8 we read for the header, and 4 for the list type.
        # Add to the size to read those bytes again.
        size += 8
        stream.seek(stream.tell() - 12)

      chunk_class = self._datadict.get(chunk_type, None)

      if not chunk_class:
        if self._chunkbase:
          module = sys.modules[self._caller.__module__]
          cls_name = '_auto__%s__%s' % (self._caller.__class__.__name__,
                                        chunk_type)
          cls_str = """class %s(%s):
                         ID = '%s'
                         pass""" % (cls_name, self._chunkbase.__name__,
                                    chunk_type)
          cls_code = compile(cls_str, '__string__', 'single', 0, 1)
          eval(cls_code, module.__dict__)
          chunk_class = module.__dict__[cls_name]

        else:
          raise AttributeError('Object has no class defined for chunk-id %s' %
                               (chunk_type))

      chunk_data = stream.read(size)
      self.append(chunk_class(raw_data=chunk_data))


def PackVar(*items):
  """Convenience function to pack strs of varying lengths.

  Args:
    items: sequence of strs.

  Returns:
    str, packed form of input values.
  """
  return ''.join(map(lambda x: struct.pack('%ds' % len(x), x), items))


def HexDump(data, cols=None):
  """Convenience function to return data as human-readable hex values.

  Args:
    data: str, binary data.
    cols: int, number of bytes to display before a line-break.

  Returns:
    str.
  """
  strs = []
  if cols:
    for i in xrange(0, len(data), cols):
      strs.append(' '.join(map(lambda x: '%02x' % ord(x),
                               data[i:i+cols])))
  else:
    strs.append(' '.join(map(lambda x: '%02x' % ord(x),
                             data[i*cols:(i+1)*cols])))

  return '\n'.join(strs)
