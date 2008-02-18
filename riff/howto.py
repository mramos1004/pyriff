#!/usr/bin/python2.4
# (C) Simon Drabble  2008
# This software is released under the Gnu General Public Licence v2.0.
# See http://www.gnu.org/licenses/old-licenses/gpl-2.0.html
"""
How to create a RIFF-compatible filespec.


Each Chunk in a RIFF file has the following format:

  4s  ID          e.g. 'WAVE'
  <I  data size   e.g. 8
  *s  data        e.g. '12345678'

data can also be a chunk, or list of chunks, e.g.

 Chunk    {  RIFF
 List     {  48                      44 = 40 + 4 (4 for WAVE)

 Wav      {    WAVE                  Wav is a LIST of chunks

 Wav      {      fmt                   ('f', 'm', 't', ' ')
 Chunk1   {      16
          {      16 bytes of data

 Wav      {      data
 Chunk2   {      10
          {      0123456789


Note that there is no constraint on the format of a Chunk's data field - it can
be a LIST, a Chunk, a string (zero-terminated or otherwise), a struct, or any
type of data at all.

This example shows how to define a class to model a RIFF structure to hold
information concerning Dwarf favourite things. The structure is defined below.
Annotations are marked by #. Items in () are placeholders. The leading numbers
show the offset within the file, where available.

00  RIFF                           # RIFF Header
04  (len)                          # filesize - 8
08  modo                           # Form(*) type. Lower-case for experimental.
0c  LIST                           # First Chunk is a LIST
10  (list-len)                     # Number of bytes in the whole LIST
14  dwrf                           # The list-type.
    {
..    (ID e.g. 'doc_')             # The Chunk ID of the list's first chunk.
..    (len)                        # The length of data in the chunk.
..    (data)                       # Chunk data
    } Repeat as many times as desired

..  addr                           # Start of the next (non-LIST) Chunk.
+4  (len)                          # Length of data in the addr chunk.
+4  (data)                         # Address data (the dwarves live together)


* - RIFF file types are called forms.


Here's a sample file. Note that binary values are marked thus: \\xx, so \\2a
means the numeric value 42. Note also that the data has been formatted to show
structure and to fit within 80 columns - in reality there would be no extraneous
whitespace in the data. All numeric binary values are little-endian.

  RIFF\\00\\00\\00\\00modo
  LIST\\34\\00\\00\\00dwrf
    doc_\\09\\00\\00\\00\\03red\\04cake
    dopy\\0e\\00\\00\\00\\06yellow\\06apples
    snzy\\0d\\00\\00\\00\\05black\\06haggis
  addr\\20\\00\\00\\001, Fairy Tale Lane\\00\\00\\00Dwarfton\\00\\00\\00\\00


With the definition of a few simple classes it will be trivial to model files
containing such data. The first task will be to model the addr structure:


  # addr is a simple Chunk. It's often a good idea to map class names direct to
  # chunk IDs, but if you have a local naming convention, use that - matching
  # names aren't a requirement.
  class addr(riff.Chunk):

The ID identifies the chunk type (RIFFs are chunks too).
    ID = 'addr'

__slots__ define the accessors for the class.
    __slots__ = ('street', 'town')

This structure has a fixed format (20 bytes for the street, 12 for the
town), so we can define a _FORMAT for it. Note that padding bytes are
appended in the sample data above. These will be included when unpacking,
but are easily dealt with.
    _FORMAT = '20s12s'

That's it for the addr Chunk. Next, we'll define a structure to hold a dwarf's
favourite information:

The name is a little different. You'll see why a bit later on.
  class dwrfStruct(riff.Chunk):

    ID = 'dwrf'
    __slots__ = ('colour', 'food')

The dwarf structure is a little different from addr. Since the fields are
variable-length, we need to override the _Unpack method of riff.Chunk:
    def _Unpack(self, data):
      l1 = struct.unpack('B', data[0])
      d1 = struct.unpack('%ds' % l1, data[1:l1+1])
      l2 = struct.unpack('B', data[l1+1])
      d2 = struct.unpack('%ds' % l2, data[l1+2:])
      return (d1, d2)

Now we'll define the class that handles unpacking the dwrf LIST:

Again, the name doesn't matter, and doesn't have to match the LIST-type, but
it helps to keep things sane if it does match.
  class dwrf(riff.LIST):

LISTs are chunks and so need an ID too.
    ID = 'dwrf'

We could, if we liked, define __slots__ here which could then be used to
access the individual dwarves in the list. Something like this:

    __slots__ = ('doc_', 'dopy', 'slpy', 'hppy', ...)

This is only useful where a LIST can contain at most one of each type.
(which is the case here: there will only be one doc_, one dopy, etc.
We could then get to the individual dwarves like this:
  dwrf.doc_
or like this:
  dwrf[0]     (also refers to dwrf.doc_)
Without __slots__, only the second form is available.

Each element in the list is a Chunk. _CLASSES tells the unpacker which
class models each chunk.

    _CLASSES = {'doc_': docStruct,
                'dopy': dopyStruct,
                'snzy', slpyStruct,
                # etc..
               }

Each sub-chunk struct will need a class looking something like this:

  class docStruct(riff.Chunk):
    ID = 'doc_'
    _FORMAT = '...'

Of course, even with such tiny classes, this can get cumbersome for large
lists - especially ones where the structs differ only by ID. Handily there
is a shortcut:

    _CHUNKBASE = SomeClass

This will generate a class for each item in __slots__ with an ID named for
the slot member. For example, the doc_ member will be mapped to an
automatically-generated class definition similar to docStruct above.
The provided class ('SomeClass') will be used as the base class for all
such generated classes.

_CHUNKBASE applies only to non-list Chunks defined within RIFF and LIST Chunks,
and requires that __slots__ is defined within the containing RIFF or LIST, which
requires that each sub-chunk appears at most once. If you have a RIFF or LIST
with sub-chunks that may appear more than once each, consider using a
MultiRecordList (described later).

It is perfectly okay to mix _CLASSES with _CHUNKBASE. This is valid:

  __slots__ = ('foo ', 'bar ')
  _CLASSES = {'foo ', SomeFoo}
  _CHUNKBASE = SomeBase

In this case, SomeFoo will be used to model 'foo ' chunks, and a temporary class
will be created to model 'bar ' chunks, inheriting from SomeBase. For a simple
class that exposes only a 'data' accessor, set _CHUNKBASE to riff.DataStruct.

For our example, we'll set _CHUNKBASE to dwrfStruct:

    _CHUNKBASE = dwrfStruct


It might seem like we've done a lot of work, but here's the full code required
to implement the Dwarf RIFF form:


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


That's it!
"""

__author__ = 'Simon Drabble <python-devel@thebigmachine.org>'
