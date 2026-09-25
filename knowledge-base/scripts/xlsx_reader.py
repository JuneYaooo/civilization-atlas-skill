"""Small read-only XLSX reader: stored scalar values, no formula evaluation."""
from pathlib import PurePosixPath
from zipfile import ZipFile
import xml.etree.ElementTree as ET
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
def sheets(path):
 with ZipFile(path) as z:
  shared=[]
  if 'xl/sharedStrings.xml' in z.namelist():
   shared=[''.join(t.text or '' for t in si.iter('{'+NS['s']+'}t')) for si in ET.fromstring(z.read('xl/sharedStrings.xml'))]
  rel={e.attrib['Id']:e.attrib['Target'] for e in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
  for sheet in ET.fromstring(z.read('xl/workbook.xml')).find('s:sheets',NS):
   target=rel[sheet.attrib['{'+R+'}id']]
   filename=target.lstrip('/') if target.startswith('/') else str(PurePosixPath('xl')/target)
   data=[]
   for row in ET.fromstring(z.read(filename)).findall('.//s:sheetData/s:row',NS):
    cells={}
    for cell in row.findall('s:c',NS):
     letters=''.join(c for c in cell.attrib['r'] if c.isalpha());col=0
     for c in letters:col=col*26+ord(c)-64
     value=cell.find('s:v',NS);value=value.text if value is not None else ''
     kind=cell.attrib.get('t')
     if kind=='s':value=shared[int(value)]
     elif kind=='inlineStr':value=''.join(t.text or '' for t in cell.findall('.//s:t',NS))
     cells[col-1]=value
    data.append((int(row.attrib['r']),[cells.get(i,'') for i in range(max(cells,default=-1)+1)]))
   yield sheet.attrib['name'],data
