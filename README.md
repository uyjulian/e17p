# e17p

## Purpose
The 'infinity series' is a set of proprietary visual novels produced by the
semi-defunct company KID ('Kindle Imagine Develop'). Various proprietary
engines for these games are available, including for Win32 and PSP, but at the
time of writing there is no Free engine capable of playing these games natively
on Unix-like OSes.

The purpose of e17p is to create such an engine by reverse-engineering the
storage formats used by these games, and writing a free parser based on the
knowledge gained this way.

Work is currently focused on Ever17, though some preliminary work has been done
on the Remember11 formats as well.

## License
GNU GPL v2, or (at your option) any later version. See the included COPYING
file for the license text for version 2.

## Dependencies
### For everything
* Python 3.x.

### For the GUI VN engine (when that gets written)
* Pygame

### For CPS->PNG conversion
* convert(1) from ImageMagick


## Formats and parsers (Ever17)
### LNK files
The top-level media data (`*.dat`) files of Ever17 are in a format that has been
dubbed 'LNK'. Almost all of the VN data used by the Ever17 engine is stored in
these files; the known exceptions are savegame data and movie files.
LNK files are simple tarball-like archives.

Extraction syntax:  
`./e17p.py ever17.ff.lnk foo.dat outdir`

### CPS files (from `bg.dat`, `chara.dat`)
CPS files contain image data. This data is both obfuscated and compressed. The
deobfuscation and decompression algorithms have been reimplemented. The actual
plaintext image format contained inside would be more appropriately referred to
as 'PRT'; however, plain PRT files have so far not been observed in the Ever17
archives, and as such the parsers for both are currently integrated.

PRT files use a bitmap format; the main image data is typically stored in RGB
with a color depth of 24 bits. Character art also includes alpha channel
information, which is stored seperately after the color bitmap.

CPS information is extracted using `./e17p.py ever17.ff.cps`. Usage modes:  
Just unobfuscation: `./e17p.py ever17.ff.cps -u foo.cps`  
Unobfuscation and decompression: `./e17p.py ever17.ff.cps -d foo.cps`  
Unobfuscate, decompress, and convert to BMP: `./e17p.py ever17.ff.cps -b foo.cps`  
(Note that standards compliance of the produced BMPs is somewhat iffy; in any
 case, some programs won't be able to read them. The primary use of this output
 mode is to feed it to convert(1) for recompression, which works fine.)

Unobfuscate, decompress, and recompress to PNG:  
`./e17p.py ever17.ff.cps -p foo.cps`  
(Being options, these can be mixed freely; see `--help` for details.)

Alternatively, this program can also be used directly on CPS-containing LNK
files, e.g.: `./e17p.py ever17.ff.cps -p -o outdir --lnk chara.dat`

### scr (`script.dat`)
Are script files, containing both text (conversation/narration) data as well as
the main game logic. We have a functioning tokenizer for the first, as well as
largely functioning tokenizer and partial parser (everything except `system.scr`
and `startup.scr` can be tokenized; semantics of many opcodes are still unknown
or questionable, however) for the second.  
See `--help` for the full list of options.  
Simple usage:  
Dump parsed colorized conversation data: `./e17p.py ever17.ff.scr -tcu foo.scr bar.scr ...`  
Dump parsed colorized event script data: `./e17p.py ever17.ff.scr -tsu foo.scr bar.scr ...`

### WAF (`bgm.dat`, `se.dat`)
Audio files for background music and sound effects; contain uncompressed data
in ADPCM format. Conversion to wav is possible using:  
`./e17p.py ever17.ff.waf foo.waf -w`

### WAF (`voice.dat`)
Audio files containing voice clips. While these have the same extension as the
files described in the previous section, the format is different in that the
entire file contents have been RLE encoded (using the same scheme as used in
CPS files) and prepended with an additional ('lnd') header. ff_dat_waf is
capable of recognizing these files by header; as such, the syntax for wav
conversion is the same as for BGM and SE WAF files:  
`./e17p.py ever17.ff.waf foo.waf -w`

### SCR (`saver.dat`)
Windows screen savers. These are stored obfuscated; the unobfuscation algorithm
has not been reimplemented yet.

### JPG (`wallpaper.dat`)
Jpeg image files, stored for wallpaper export. These are stored obfuscated,
using essentially the same obfuscation algorithm as for SCR files.

### WAV (`sysvoice.dat`)
Wave audio files, stored for system voice set export. These are stored
obfuscated, using essentially the same obfuscation algorithm as for SCR files.


## Formats and parsers (Remember11)
### AFS files
Are top-level aggregates of smaller files. Aside from file contents, they also
store names and various metadata of unknown meaning. This file format includes
an RLE compression algorithm that works on a per-file basis, and a single AFS
archive can contain both compressed and uncompressed files in arbitrary
combination.

### BIP files (`mac.afs`)
Event scripts, possibly mixed with other data. There's an experimental and
incomplete tokenizer for the script bytecode; recommended usage:  
`./e17p.py remember11.ff.event_script -qrtu --afs --cont mac.afs`

### T2P files (`chr.afs`, `ev.afs`)
Image files that come in two flavors: BGRA bitmap images, and wrapped PNG
files. The T2P header is 64 bytes; wrapped PNG get an additional inner header
that always starts with the bytes 'PNGFILE', and is another 124 bytes in
length. A converter script from both types to PNG is available; usage example:  
`./e17p.py remember11.ff.t2p -o outdir --png --afs chr.afs`

