#!/usr/bin/python2.4
# (C) Simon Drabble  2008
# This software is released under the Gnu General Public Licence v2.0.
# See http://www.gnu.org/licenses/old-licenses/gpl-2.0.html


__author__ = 'Simon Drabble <python-devel@thebigmachine.org>'


import struct
from StringIO import StringIO
import unittest
import riff


class MockSimpleRiff(riff.RIFF):

  ID = 'test'


class MockFooChunk(riff.Chunk):

  ID = 'foo '
  __slots__ = ('frob', 'nitz')
  _FORMAT = '<I6s'


class MockBarChunk(riff.Chunk):

  ID = 'bar '
  __slots__ = ('goober', 'rutabaga')
  _FORMAT = '<BB'


class MockRiffWithChunks(riff.RIFF):

  ID = 'test'
  __slots__ = ('foo', 'bar')
  _CLASSES = {'foo ': MockFooChunk,
              'bar ': MockBarChunk,
             }


class MockHerbChunk(riff.Chunk):

  ID = 'herb'
  __slots__ = ('chervil', 'sage')
  _FORMAT = '<II'


class MockSpceChunk(riff.Chunk):

  ID = 'spce'
  __slots__ = ('nutmeg', 'paprika')
  _FORMAT = '<IH'


class MockListForRiffWithList(riff.LIST):

  ID = 'tlst'
  __slots__ = ('herb', 'spce')
  _CLASSES = {'herb': MockHerbChunk,
              'spce': MockSpceChunk}
  # TODO: test _CLASSES as a tuple, to be used where no __slots__ exist.


class MockRiffWithList(riff.RIFF):

  ID = 'Tlst'
  __slots__ = ('tlst',)
  _CLASSES = {'tlst': MockListForRiffWithList}


class MockDwarfStruct(riff.Chunk):

  __slots__  = ('colour', 'food')

  def _Unpack(self, data):
    l1, = struct.unpack('B', data[0])
    d1, = struct.unpack('%ds' % l1, data[1:l1+1])
    l2, = struct.unpack('B', data[l1+1])
    d2, = struct.unpack('%ds' % l2, data[l1+2:])
    return (d1, d2)


class MockDwrfList(riff.LIST):

  ID = 'dwrf'
  __slots__ = ('doc_', 'dopy', 'snzy')
  _CHUNKBASE = MockDwarfStruct


class MockDwrfAddr(riff.Chunk):

  ID = 'addr'
  __slots__ = ('street', 'city')
  _FORMAT = '20s12s'


class MockDwarfRiff(riff.RIFF):

  ID = 'modo'
  __slots__ = ('dwrf', 'addr')
  _CLASSES = {'dwrf': MockDwrfList,
              'addr': MockDwrfAddr}


class FromStreamTest(unittest.TestCase):

  def testRiffFromStreamSimple(self):
    packed = struct.pack('<4sI4s', 'RIFF', 4, 'test')
    the_riff = MockSimpleRiff(stream=StringIO(packed))
    self.assertEqual(packed, repr(the_riff))

  def testRiffWithChunks(self):
    packed = struct.pack('<4sI4s4sII6s4sIBB', 'RIFF', 32,
                         'test',
                         'foo ', 10, 42, '3.1415',
                         'bar ', 2, 255, 128)
    the_riff = MockRiffWithChunks(stream=StringIO(packed))
    self.assertEqual(packed, repr(the_riff))
    self.assertEqual(42, the_riff[0].frob)
    self.assertEqual('3.1415', the_riff[0].nitz)
    self.assertEqual(255, the_riff[1].goober)
    self.assertEqual(128, the_riff[1].rutabaga)

  def testListDecode(self):
    packed = struct.pack('<4sI4s4sIII4sIIH',
                         'LIST', 34, 'tlst',
                         'herb', 8, 4, 42,
                         'spce', 6, 2, 65535)
    the_riff = MockListForRiffWithList(stream=StringIO(packed))
    self.assertEqual(packed, repr(the_riff))
    # Two! Two methods of accessing items!
    self.assertEqual(42, the_riff[0].sage)
    self.assertEqual(42, the_riff.herb.sage)

  def testRiffWithList(self):
    packed = struct.pack('<4sI4s4sI4s4sIII4sIIH',
                         'RIFF', 46, 'Tlst',
                         'LIST', 34, 'tlst',
                         'herb', 8, 4, 42,
                         'spce', 6, 2, 65535)
    the_riff = MockRiffWithList(stream=StringIO(packed))
    self.assertEqual(packed, repr(the_riff))
    self.assertEqual(4, the_riff[0].herb.chervil)
    self.assertEqual(42, the_riff[0].herb.sage)
    self.assertEqual(2, the_riff.tlst.spce.nutmeg)

  def testDwarves(self):
    packed = struct.pack('<4sI4s4sI4s4sIB3sB4s4sIB6sB6s4sIB5sB6s4sI20s12s',
                         'RIFF', 112, 'modo',
                         'LIST', 64, 'dwrf',
                         'doc_', 9, 3, 'red', 4, 'cake',
                         'dopy', 14, 6, 'yellow', 6, 'apples',
                         'snzy', 13, 5, 'black', 6, 'haggis',
                         'addr', 32, '1, Fairy Tale Lane\0\0\0',
                         'Dwarfton\0\0\0\0')
    the_riff = MockDwarfRiff(raw_data=packed)
    self.assertEqual('red', the_riff.dwrf.doc_.colour)
    self.assertEqual('cake', the_riff.dwrf.doc_.food)
    self.assertEqual('yellow', the_riff.dwrf[1].colour)
    self.assertEqual('apples', the_riff.dwrf.dopy.food)
    self.assertEqual('black', the_riff.dwrf.snzy.colour)
    self.assertEqual('haggis', the_riff.dwrf[2].food)


if __name__ == '__main__':
  unittest.main()
