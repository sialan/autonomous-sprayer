#!/usr/bin/env python
#coding:utf-8
# Author:  mozman
# Purpose: table, consisting of basic R12 entities
# module belongs to package: dxfwrite.py
# Created: 18.03.2010
# Copyright (C) 2010, Manfred Moitzi
# License: GPLv3
"""
Table object like a HTML-Table, buildup with DXF R12 entities.

Cells can contain Multiline-Text or DXF-BLOCKs, or you can create your own
cell-type by extending the CustomCell object.
Cells can span over columns and rows.
Text cells can contain text with an arbitrary rotation angle, or letters can be
stacked top-to-bottom.
BlockCells contains block references (INSERT-entity) created from a block
definition (BLOCK), if the block definition contains attribute definitions
(ATTDEF-entity), attribs created by Attdef.new_attrib() will be added to the
block reference (ATTRIB-entity).
"""
import sys
if sys.version_info[0] > 2:
    xrange = range

from array import array
from copy import deepcopy

import dxfwrite.const as const
from dxfwrite.base import DXFList
from dxfwrite.entities import Line, Solid, Insert
from dxfwrite.mtext import MText

__all__ = ['Table', 'CustomCell']

DEFAULT_TABLE_BGLAYER = 'TABLEBACKGROUND'
DEFAULT_TABLE_FGLAYER = 'TABLECONTENT'
DEFAULT_TABLE_GRIDLAYER = 'TABLEGRID'
DEFAULT_TABLE_HEIGHT = 1.0
DEFAULT_TABLE_WIDTH  = 2.5
DEFAULT_TEXTSTYLE = 'STANDARD'
DEFAULT_CELL_TEXT_HEIGHT = 0.7
DEFAULT_CELL_LINESPACING = 1.5
DEFAULT_CELL_XSCALE = 1.0
DEFAULT_CELL_YSCALE = 1.0
DEFAULT_CELL_HALIGN = const.LEFT
DEFAULT_CELL_VALIGN = const.TOP
DEFAULT_CELL_TEXTCOLOR = const.BYLAYER
DEFAULT_CELL_BG_COLOR = None
DEFAULT_CELL_HMARGIN = 0.1
DEFAULT_CELL_VMARGIN = 0.1
DEFAULT_BORDER_COLOR = 5
DEFAULT_BORDER_LINETYPE = None
DEFAULT_BORDER_STATUS = True
DEFAULT_BORDER_PRIORITY = 50

VISIBLE = 1
HIDDEN = 0

class Table(object):
    """A HTML-table like object.

    The table object contains the table data cells.
    """
    name = 'TABLE'

    def __init__(self, insert, nrows, ncols, default_grid=True):
        """
        :param insert: insert point as 2D or 3D point
        :param int nrows: row count
        :param int ncols: column count
        :param bool default_grid: if **True** always a solid line grid will
            be drawn, if **False**, only explicit defined borders will be
            drawn, default grid has a priority of 50.
        """
        self.insert = insert
        self.nrows = nrows
        self.ncols = ncols
        self.row_heights = [DEFAULT_TABLE_HEIGHT] * nrows
        self.col_widths = [DEFAULT_TABLE_WIDTH] * ncols
        self.bglayer = DEFAULT_TABLE_BGLAYER
        self.fglayer = DEFAULT_TABLE_FGLAYER
        self.gridlayer = DEFAULT_TABLE_GRIDLAYER
        self.styles = {'default': Style.get_default_cell_style()}
        if not default_grid:
            default_style = self.get_cell_style('default')
            default_style.set_border_status(False, False, False, False)

        self._cells = {} # data cells
        self.frames = [] # border frame objects
        # visibility_map stores the visibilty of the cells, created in _setup
        self.visibility_map = None
        # grid manages the border lines, created in _setup
        self.grid = None
        # data contains the resulting dxf entities
        self.data = DXFList()
        self.empty_cell = Cell(self) # represents all empty cells

    def set_col_width(self, column, value):
        """Set column width of **column** to **value** (in drawing units).
        """
        self.col_widths[column] = float(value)

    def set_row_height(self, row, value):
        """Set row heigth of **row** to **value** (in drawing units).
        """
        self.row_heights[row] = float(value)

    def text_cell(self, row, col, text, span=(1, 1), style='default'):
        """Create a new text cell at pos (**row**, **col**), with **text** as
        content, text can be a multi line text, use ``'\\n'`` as line
        seperator.

        The cell spans over **span** cells and has the cell style with the
        name **style**.
        """
        cell = TextCell(self, text, style=style, span=span)
        return self.set_cell(row, col, cell)

    # pylint: disable-msg=W0102
    def block_cell(self, row, col, blockdef, span=(1, 1), attribs={}, style='default'):
        """Create a new block cell at position (**row**, **col**), content is
        a block reference inserted by a :ref:`INSERT` entity, attributes will
        be added if the block definition contains :ref:`ATTDEF`. Assignments
        are defined by attribs-key to attdef-tag association.
        Example: attribs = {'num': 1} if an :ref:`ATTDEF` with tag=='num' in
        the block definition exists, an attrib with text=str(1) will be
        created and added to the insert entity.

        The cell spans over **span** cells and has the cell style with the
        name **style**.
        """
        cell = BlockCell(self, blockdef, style=style, attribs=attribs, span=span)
        return self.set_cell(row, col, cell)

    def set_cell(self, row, col, cell):
        """Insert a **cell** at position (**row**, **col**)."""
        row, col = self.validate_index(row, col)
        self._cells[row, col] = cell
        return cell

    def get_cell(self, row, col):
        """Get cell at position (**row**, **col**)."""
        row, col = self.validate_index(row, col)
        try:
            return self._cells[row, col]
        except KeyError:
            return self.empty_cell # emtpy cell with default style

    def validate_index(self, row, col):
        row = int(row)
        col = int(col)
        if row < 0 or row >= self.nrows or \
           col < 0 or col >= self.ncols:
            raise IndexError('cell index out of range')
        return row, col

    def frame(self, row, col, width=1, height=1, style='default'):
        """Create a Frame object which frames the cell area starting at
        **row**, **col** covering **widths** columns and **heigth** rows.
        """
        frame = Frame(self, pos=(row, col), span=(height, width),
                      style=style)
        self.frames.append(frame)
        return frame

    def new_cell_style(self, name, **kwargs):
        """Create a new Style object with the name **name**.

        :param kwargs: see Style.get_default_cell_style()
        """
        style = deepcopy(self.get_cell_style('default'))
        style.update(kwargs)
        self.styles[name] = style
        return style

    def new_border_style(self, color=const.BYLAYER, status=True,
                         priority=100, linetype=None):
        """Create a new border style.

        :param bool status: if **True** border is visible, **False** border
            is hidden
        :param int color: dxf color index
        :param string linetype: linetype name, BYLAYER if None
        :param int priority: drawing priority - higher values covers lower
            values
        """
        border_style = Style.get_default_border_style()
        border_style['color'] = color
        border_style['linetype'] = linetype
        border_style['status'] = status
        border_style['priority'] = priority
        return border_style

    def get_cell_style(self, name):
        """Get cell style by **name**.
        """
        return self.styles[name]

    def iter_visible_cells(self):
        """Iterate over all visible cells.

        returns a generator which yields all visible cells as tuples:
        **row**, **col**, **cell**
        """
        if self.visibility_map is None:
            raise Exception("Can only be called at dxf creation.")
        return ((row, col, self.get_cell(row, col))
                for row, col in self.visibility_map)

    def __dxf__(self):
        self._build_table()
        result = self.data.__dxf__()
        self.data = DXFList() # don't need to keep this data in memory
        return result

    def _setup(self):
        """Table generation setup."""
        self.visibility_map = VisibilityMap(self, status=VISIBLE)
        self.grid = Grid(self)

    def _build_table(self):
        """Table is generated on calling the __dxf__() method."""
        self._setup()
        self.grid.draw_lines()
        for row, col, cell in self.iter_visible_cells():
            self.grid.draw_cell_background(row, col, cell)
            self.grid.draw_cell_content(row, col, cell)
        self._cleanup()

    def _cleanup(self):
        """Table generation cleanup. """
        self.visibility_map = None
        self.grid = None

class VisibilityMap(object):
    """Stores the visibility of table cells."""
    def __init__(self, table, status):
        """Constructor

        table -- the table entity
        status -- init status value
        """
        self.table = table
        self._cells = array('B', (status for _ in xrange(self.table.nrows*self.table.ncols)))
        self._create_visibility_map()

    def _create_visibility_map(self):
        """Set visibility for all existing cells."""
        for row, col in iter(self):
            cell = self.table.get_cell(row, col)
            self._set_span_visibility(row, col, cell.span)

    def _set_span_visibility(self, row, col, span):
        """Set the visibilty of the given cell. The cell itself is
        visible, all other cells in the span-range (tuple: width, height) are
        invisible, they are covered by the main cell <row>, <col>."""
        if span != (1, 1):
            for rowx in xrange(span[0]):
                for colx in xrange(span[1]):
                    # switch all cells in span range to invisible
                    self.hide(row+rowx, col+colx)
        # switch content cell visible
        self.show(row, col)

    def _get_index(self, row, col):
        """Calculate the liniear array index."""
        return row*self.table.ncols+col

    def get(self, row, col):
        """Get visibility status of cell <row>, <col>.
        returns HIDDEN or VISIBLE
        """
        return self._cells[self._get_index(row, col)]

    def show(self, row, col):
        """Set cell <row>, <col> status to VISIBLE."""
        self._cells[self._get_index(row, col)] = VISIBLE

    def hide(self, row, col):
        """Set cell <row>, <col> status to HIDDEN."""
        self._cells[self._get_index(row, col)] = HIDDEN

    def iter_all_cells(self):
        """Iterate over all cell indices, yields <row>, <col> tuples."""
        for row in xrange(self.table.nrows):
            for col in xrange(self.table.ncols):
                yield (row, col)

    def is_visible_cell(self, row, col):
        """True if cell <row>, <col>  is visible, else False"""
        return self.get(row, col) == VISIBLE

    def __iter__(self):
        """Iterate over all visible cells."""
        return ( (row, col) for (row, col) in self.iter_all_cells() \
                 if self.is_visible_cell(row, col) )

class Style(dict):
    """Cell style object."""
    @staticmethod
    def get_default_cell_style():
        return Style({
            # textstyle is ignored by block cells
            'textstyle': 'STANDARD',
            # text height in drawing units, ignored by block cells
            'textheight': DEFAULT_CELL_TEXT_HEIGHT,
            # line spacing in percent = <textheight>*<linespacing>, ignored by block cells
            'linespacing': DEFAULT_CELL_LINESPACING,
            # text stretch or block reference x-axis scaling factor
            'xscale': DEFAULT_CELL_XSCALE,
            # block reference y-axis scaling factor, ignored by text cells
            'yscale': DEFAULT_CELL_YSCALE,
            # dxf color index, ignored by block cells
            'textcolor': DEFAULT_CELL_TEXTCOLOR,
            # text or block rotation in degrees
            'rotation' : 0.,
            # Letters are stacked top-to-bottom, but not rotated
            'stacked': False,
            # horizontal alignment (const.LEFT, const.CENTER, const.RIGHT)
            'halign': DEFAULT_CELL_HALIGN,
            # vertical alignment (const.TOP, const.MIDDLE, const.BOTTOM)
            'valign': DEFAULT_CELL_VALIGN,
            # left and right margin in drawing units
            'hmargin': DEFAULT_CELL_HMARGIN,
            # top and bottom margin
            'vmargin': DEFAULT_CELL_VMARGIN,
            # background color, dxf color index, ignored by block cells
            'bgcolor': DEFAULT_CELL_BG_COLOR,
            # left border style
            'left': Style.get_default_border_style(),
            # top border style
            'top': Style.get_default_border_style(),
            # right border style
            'right': Style.get_default_border_style(),
            # bottom border style
            'bottom': Style.get_default_border_style(),
        })

    @staticmethod
    def get_default_border_style():
        return {
            # border status, True for visible, False for hidden
            'status': DEFAULT_BORDER_STATUS,
            # dxf color index
            'color': DEFAULT_BORDER_COLOR,
            # linetype name, BYLAYER if None
            'linetype': DEFAULT_BORDER_LINETYPE,
            # drawing priority, higher values cover lower values
            'priority': DEFAULT_BORDER_PRIORITY,
        }

    def set_border_status(self, left=True, right=True, top=True, bottom=True):
        """Set status of all cell borders at once."""
        for border, status in (('left', left),
                               ('right', right),
                               ('top', top),
                               ('bottom', bottom)):
            self[border]['status'] = status

    def set_border_style(self, style,
                         left=True, right=True, top=True, bottom=True):
        """Set border styles of all cell borders at once."""
        for border, status in (('left', left),
                               ('right', right),
                               ('top', top),
                               ('bottom', bottom)):
            if status:
                self[border] = style

class Grid(object):
    """Grid contains the graphical representation of the table."""
    def __init__(self, table):
        """Constructor

        table -- assigned data table
        """
        self.table = table
        # contains the x-axis coords of the grid lines between the data columns.
        self.col_pos = self._calc_col_pos()
        # contains the y-axis coords of the grid lines between the data rows.
        self.row_pos = self._calc_row_pos()
        # contans the horizontal border elements, list of border styles
        # get index with _border_index(row, col), which means the border element
        # above row, col, and row-indices are [0 .. nrows+1], nrows+1 for the
        # grid line below the last row; list contains only the border style with
        # the highest priority.
        self._hborders = None # created in _init_borders
        # same as _hborders but for the vertical borders,
        # col-indices are [0 .. ncols+1], ncols+1 for the last grid line right
        # of the last column
        self._vborders = None # created in _init_borders
        # border style to delete border inside of merged cells
        self.noborder = dict(status=False, priority=999, linetype=None, color=0)

    def _init_borders(self, hborder, vborder):
        """Init the _hborders with  <hborder> and _vborders with <vborder>."""
        # <border_count> has more elements than necessary, but it unifies the
        # index calculation for _vborders and _hborders.
        # exact values are:
        # hborder_count = ncols * (nrows+1), hindex = ncols * <row> + <col>
        # vborder_count = nrows * (ncols+1), vindex = (ncols+1) * <row> + <col>
        border_count = (self.table.nrows+1) * (self.table.ncols+1)
        self._hborders = [hborder] * border_count
        self._vborders = [vborder] * border_count

    def _border_index(self, row, col):
        """Calculate linear index for border arrays _hborders and _vborders."""
        return row * (self.table.ncols+1) + col

    def set_hborder(self, row, col, border_style):
        """Set <border_style> for the horizontal border element above <row>, <col>."""
        return self._set_border_style(self._hborders, row, col, border_style)

    def set_vborder(self, row, col, border_style):
        """Set <border_style> for the vertical border element left of <row>, <col>."""
        return self._set_border_style(self._vborders, row, col, border_style)

    def _set_border_style(self, borders, row, col, border_style):
        """Set <border_style> for <row>, <col> in <borders>. """
        border_index = self._border_index(row, col)
        actual_borderstyle = borders[border_index]
        if border_style['priority'] >= actual_borderstyle['priority']:
            borders[border_index] = border_style

    def get_hborder(self, row, col):
        """Get the horizontal border element above <row>, <col>.
        Last grid line (below <nrows>) is the element above of <nrows+1>.
        """
        return self._get_border(self._hborders, row, col)

    def get_vborder(self, row, col):
        """Get the vertical border element left of <row>, <col>.
        Last grid line (right of <ncols>) is the element left of <ncols+1>.
        """
        return self._get_border(self._vborders, row, col)

    def _get_border(self, borders, row, col):
        """Get border element at <row>, <col> from <borders>."""
        return borders[self._border_index(row, col)]

    def _sum_fields(self, start_value, fields, append, sign=1.):
        """adds step-by-step the fields-values, starting with <start_value>,
        and appends the resulting values to an other object with the
        append-method.
        """
        position = start_value
        append(position)
        for element in fields:
            position += element * sign
            append(position)

    def _calc_col_pos(self):
        """Calculate the x-axis coords of the grid lines between the columns."""
        col_pos = array('f')
        start_x = self.table.insert[0]
        self._sum_fields(start_x,
                         self.table.col_widths,
                         col_pos.append)
        return col_pos

    def _calc_row_pos(self):
        """Calculate the y-axis coords of the grid lines between the rows."""
        row_pos = array('f')
        start_y = self.table.insert[1]
        self._sum_fields(start_y,
                         self.table.row_heights,
                         row_pos.append, -1.)
        return row_pos

    def cell_coords(self, row, col, span):
        """Get the coordinates of the cell <row>,<col> as absolute drawing units.
        returns a tuple (left, right, top, bottom)
        """
        top = self.row_pos[row]
        bottom = self.row_pos[row+span[0]]
        left = self.col_pos[col]
        right = self.col_pos[col+span[1]]
        return (left, right, top, bottom)

    def draw_cell_background(self, row, col, cell):
        """Draw the cell background for <row>, <col> as DXF-SOLID entity."""
        style = cell.style
        if style['bgcolor'] is None:
            return
        # get cell coords in absolute drawing units
        left, right, top, bottom = self.cell_coords(row, col, cell.span)
        ltop = (left, top)
        lbot = (left, bottom)
        rtop = (right, top)
        rbot = (right, bottom)
        self.table.data.append(Solid(
            points=[ltop, lbot, rbot, rtop],
            color=style['bgcolor'],
            layer=self.table.bglayer))

    def draw_cell_content(self, row, col, cell):
        """Draw the cell content for <row>,<col>, calls the cell
        method <cell>.get_dxf_entity() (has to return an object with a __dxf__()
        method) to create the cell content.
        """
        # get cell coords in absolute drawing units
        coords = self.cell_coords(row, col, cell.span)
        dxf_entity = cell.get_dxf_entity(coords, self.table.fglayer)
        self.table.data.append(dxf_entity)

    def draw_lines(self):
        """Draw all grid lines."""
        # Init borders with default_style top- and left border.
        default_style = self.table.get_cell_style('default')
        hborder = default_style['top']
        vborder = default_style['left']
        self._init_borders(hborder, vborder)
        self._set_frames(self.table.frames)
        self._set_borders(self.table.iter_visible_cells())
        self._draw_borders(self.table)

    def _set_borders(self, visible_cells):
        """Set borders of the visible cells."""
        for row, col, cell in visible_cells:
            bottom_row = row + cell.span[0]
            right_col = col + cell.span[1]
            self._set_rect_borders(row, bottom_row, col, right_col, cell.style)
            self._set_inner_borders(row, bottom_row, col, right_col,
                                    self.noborder)


    def _set_inner_borders(self, top_row, bottom_row, left_col, right_col, border_style):
        """Set <border_style> to the inner borders of the rectangle <top_row...
        """
        if bottom_row - top_row > 1:
            for col in xrange(left_col, right_col):
                for row in xrange(top_row+1, bottom_row):
                    self.set_hborder(row, col, border_style)
        if right_col - left_col > 1:
            for row in xrange(top_row, bottom_row):
                for col in xrange(left_col+1, right_col):
                    self.set_vborder(row, col, border_style)

    def _set_rect_borders(self, top_row, bottom_row, left_col, right_col, style):
        """Set border <style> to the rectangle <top_row><bottom_row...
        The values describing the grid lines between the cells, see doc-strings
        for set_hborder and set_vborder and see comments for self._hborders and
        self._vborders.
        """
        for col in xrange(left_col, right_col):
            self.set_hborder(top_row, col, style['top'])
            self.set_hborder(bottom_row, col, style['bottom'])
        for row in xrange(top_row, bottom_row):
            self.set_vborder(row, left_col, style['left'])
            self.set_vborder(row, right_col, style['right'])

    def _set_frames(self, frames):
        """Set borders for all defined frames."""
        for frame in frames:
            top_row = frame.pos[0]
            left_col = frame.pos[1]
            bottom_row = top_row + frame.span[0]
            right_col = left_col + frame.span[1]
            self._set_rect_borders(top_row, bottom_row, left_col, right_col,
                                  frame.style)
    def _draw_borders(self, table):
        """Draw the grid lines as DXF-LINE entities."""
        def append_line(start, end, style):
            """ Appends the DXF-LINE entity to the table dxf data. """
            if style['status']:
                table.data.append(Line(
                    start=start,
                    end=end,
                    layer=layer,
                    color=style['color'],
                    linetype=style['linetype']))

        def draw_hborders():
            """Draw the horizontal grid lines."""
            for row in xrange(table.nrows+1):
                yrow = self.row_pos[row]
                for col in xrange(table.ncols):
                    xleft = self.col_pos[col]
                    xright = self.col_pos[col+1]
                    style = self.get_hborder(row, col)
                    append_line((xleft, yrow), (xright, yrow), style)

        def draw_vborders():
            """ Draw the vertical grid lines."""
            for col in xrange(table.ncols+1):
                xcol = self.col_pos[col]
                for row in xrange(table.nrows):
                    ytop = self.row_pos[row]
                    ybottom = self.row_pos[row+1]
                    style = self.get_vborder(row, col)
                    append_line((xcol, ytop), (xcol, ybottom), style)

        layer = table.gridlayer
        draw_hborders()
        draw_vborders()

class Frame(object):
    """Represent a rectangle cell area enclosed with a border lines."""
    def __init__(self, table, pos=(0, 0), span=(1 ,1), style='default'):
        """Constructor

        table -- the assigned data table
        pos -- tuple (row, col), border goes left and top of pos
        span -- count of cells that Frame covers, border goes right and below
            of this cells
        style -- style name as string
        """
        self.table = table
        self.pos = pos
        self.span = span
        self.stylename = style

    @property
    def style(self):
        """Get the style object from table."""
        return self.table.get_cell_style(self.stylename)

class Cell(object):
    """Cell represents the table cell data."""

    def get_span(self):
        return self._span
    def set_span(self, value):
        """Ensures that span values are >= 1 in each direction."""
        self._span = (max(1, value[0]), max(1, value[1]))
    span = property(get_span, set_span)

    def __init__(self, table, style='default', span=(1, 1)):
        """Constructor

        table -- assigned data table
        style -- style name as string
        span -- tuple(spanrows, spancols), count of cells that cell covers

        Cell does not know its own position in the data table, because a cell
        can be used multiple times in the same or in different tables.
        And therefore the cell itself can not determine if the cell-range
        reaches beyond the table borders.
        """
        self.table = table
        self.stylename = style
        # span values has to be >= 1
        self.span = span

    # pylint: disable-msg=W0613
    def get_dxf_entity(self, coords, layer):
        return DXFList()

    def substract_margin(self, coords):
        """Reduces the cell-coords about the hmargin and the vmargin values."""
        hmargin = self.style['hmargin']
        vmargin = self.style['vmargin']
        return ( coords[0]+hmargin, # left
                 coords[1]-hmargin, # right
                 coords[2]-vmargin, # top
                 coords[3]+vmargin ) # bottom
    @property
    def style(self):
        """Get the style object from table."""
        return self.table.get_cell_style(self.stylename)

class TextCell(Cell):
    """Represents a multi line text. Text lines are separated by '\n'."""
    def __init__(self, table,  text, style='default', span=(1, 1)):
        """Constructor

        table -- assigned data table
        text -- multi line text, lines separated by '\n'
        style -- style name as string
        span -- tuple(spanrows, spancols), count of cells that cell covers

        see Cell.__init__()
        """
        super(TextCell, self).__init__(table, style, span)
        self.text = text

    def get_dxf_entity(self, coords, layer):
        """Create the cell content as MText-object.

        coords -- tuple of border-coordinates : left, right, top, bottom
        layer -- layer, which should be used for dxf entities
        """
        if len(self.text) == 0:
            return DXFList()
        left, right, top, bottom = self.substract_margin(coords)
        style = self.style
        halign = style['halign']
        valign = style['valign']
        rotated = self.style['rotation']
        text = self.text
        if style['stacked']:
            rotated = 0.
            text = '\n'.join( (char for char in self.text.replace('\n', ' ')) )
        xpos = (left, float(left+right)/2., right)[halign]
        ypos = (bottom, float(bottom+top)/2., top)[valign-1]
        return MText(text, (xpos, ypos),
                     linespacing=self.style['linespacing'],
                     style=self.style['textstyle'],
                     height=self.style['textheight'],
                     rotation=rotated,
                     xscale=self.style['xscale'],
                     halign=halign,
                     valign=valign,
                     color=self.style['textcolor'],
                     layer=layer)

class CustomCell(Cell):
    """ Cell with 'user' controlled content. """
    def __init__(self, table, style='default', span=(1, 1)):
        """Constructor

        table -- assigned data table
        style -- style name as string
        span -- tuple(spanrows, spancols), count of cells that cell covers

        see Cell.__init__()
        """
        super(CustomCell, self).__init__(table, style, span)

    def get_dxf_entity(self, coords, layer):
        """ override this methode and create an arbitrary dxf element

        coords -- tuple of border-coordinates : left, right, top, bottom
        layer -- layer, which should be used for dxf entities
        """
        # get access to all style parameter
        style = self.style # pylint: disable-msg=W0612
        # reduce borders about hmargin and vmargin
        # pylint: disable-msg=W0612
        left, right, top, bottom = self.substract_margin(coords)
        # and now do what you want ...
        # return a dxf entity which implement the __dxf__ protocoll
        # DXFList is a good choice
        raise NotImplementedError()


class BlockCell(Cell):
    """ Cell that contains a block reference. """
    # pylint: disable-msg=W0102
    def __init__(self, table, blockdef, style='default', attribs={}, span=(1, 1)):
        """Constructor

        table -- assigned data table
        blockdef -- block definition to insert (as INSERT-entity), but i need
            the blockdef for to create the ATTRIB-entities
        attribs -- dict, where key==tag from the ATTDEF-entity
        style -- style name as string
        span -- tuple(spanrows, spancols), count of cells that cell covers

        see Cell.__init__()
        """

        super(BlockCell, self).__init__(table, style, span)
        self.blockdef = blockdef # dxf block definition!
        self.attribs = attribs

    def get_dxf_entity(self, coords, layer):
        """Create the cell content as INSERT-entity with trailing
        ATTRIB-entities.

        coords -- tuple of border-coordinates : left, right, top, bottom
        layer -- layer, which should be used for dxf entities
        """
        left, right, top, bottom = self.substract_margin(coords)
        style = self.style
        halign = style['halign']
        valign = style['valign']
        xpos = (left, float(left+right)/2., right)[halign]
        ypos = (bottom, float(bottom+top)/2., top)[valign-1]
        insert = Insert(blockname=self.blockdef['name'],
                        insert=(xpos, ypos),
                        xscale=style['xscale'],
                        yscale=style['yscale'],
                        rotation=style['rotation'],
                        layer=layer)
        # process attribs
        for key, value in self.attribs.items():
            try:
                attdef = self.blockdef.find_attdef(key)
                attrib = attdef.new_attrib(text=str(value))
                insert.add(attrib, relative=True)
            except KeyError:
                pass # ignore none existing attdefs
        return insert
