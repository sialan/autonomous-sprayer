# draw_create.py  Alan Si(asi@uwo.ca)
# this file creates a real sized dxf mapping of the Research-o-Matic's stage/toolpath
# all units are in mm

from dxfwrite import DXFEngine as dxf
from math import floor

def dxf_render(pattern, x, y, spacing):
  drawing = dxf.drawing("spray_pattern.dxf")
  drawing.add_layer("2D")

  # if the spacing does not correlate perfectly with sample size, Research-o-Matic will add another loop to overspray and ensure coverage
  if y % spacing != 0:
    y = floor(y) + spacing 

  if pattern == "grid": # classic square grid pattern
    horline = 0
    vertline = 0
    if x % spacing != 0:
      x = floor(x) + spacing
    while horline <= y :
        drawing.add(dxf.line((0, horline), (x, horline), color=7, layer="2D"))
        horline += spacing
    while vertline < x:
        drawing.add(dxf.line((vertline, 0), (vertline, y), color=7, layer="2D"))
        vertline += spacing

  elif pattern == "horlines": # a collection of uni-directional lines sprayed horizontally (x-direction) going from left to right(-x to +x)
    horline = 0
    while horline <= y :
      drawing.add(dxf.line((0, horline), (x, horline), color=7, layer="2D"))
      horline += spacing
   
  else: # default pattern of "snakes" from the eponymous game
    horline = 0
    vertlineright = 0
    vertlineleft = spacing
    while horline <= y :
        drawing.add(dxf.line((0, horline), (x, horline), color=7, layer="2D"))
        horline += spacing
    while vertlineright < y:
        drawing.add(dxf.line((x, vertlineright), (x, vertlineright + spacing), color=7, layer="2D"))
        vertlineright += 2 * spacing
    while vertlineleft < y:
        drawing.add(dxf.line((0, vertlineleft), (0, vertlineleft + spacing), color=7, layer="2D"))
        vertlineleft += 2 * spacing
  drawing.saveas("spray_pattern.dxf")
 