#!/usr/bin/env python
#coding:utf-8
# Author:  mozman
# Purpose: curve objects
# Created: 26.03.2010
# Copyright (C) 2010, Manfred Moitzi
# License: GPLv3
from math import sin, cos, radians, fmod

import sys
if sys.version_info[0] > 2:
    xrange = range

from dxfwrite.vector2d import vadd
import dxfwrite.const as const
#from dxfwrite.base import DXFList
from dxfwrite.entities import Polyline
from dxfwrite.algebra import rotate_2d, equals_almost
from dxfwrite.algebra import CubicSpline, CubicBezierCurve
from dxfwrite.algebra import Clothoid as _ClothoidValues

__all__ = ['Ellipse', 'Bezier', 'Spline', 'Clothoid']

class Ellipse(object):
    def __init__(self, center=(0., 0., 0.), rx=1.0, ry=1.0,
                 startangle=0., endangle=360., rotation=0., segments=100,
                 color=const.BYLAYER, layer='0', linetype=None):
        self.color = color
        self.layer = layer
        self.linetype = linetype
        self.center = center
        self.rx = float(rx)
        self.ry = float(ry)
        self.startangle = float(startangle)
        self.endangle = float(endangle)
        self.rotation = float(rotation)
        self.segments = int(segments)

    def _build_curve(self):
        def curve_point(alpha):
            alpha = radians(alpha)
            point = (cos(alpha) * self.rx,
                     sin(alpha) * self.ry)
            point = rotate_2d(point, radians(self.rotation))
            x, y = vadd(self.center, point)
            return (x, y, zaxis)

        def normalize_angle(angle):
            angle = fmod(angle, 360.)
            if angle < 0:
                angle += 360.
            return angle

        zaxis = 0. if len(self.center)<3 else self.center[2]
        points = []
        delta = (self.endangle - self.startangle) / self.segments
        for segment in xrange(self.segments):
            alpha = self.startangle + delta * segment
            points.append(curve_point(alpha))
        polyline = Polyline(points, color=self.color, layer=self.layer,
                            linetype=self.linetype)

        if equals_almost(self.startangle, normalize_angle(self.endangle)):
            polyline.close()
        return polyline

    def __dxf__(self):
        return self._build_curve().__dxf__()

class Bezier(object):
    class Segment(object):
        def __init__(self, start, end, start_tangent, end_tangent, segments):
            self.start = start
            self.end = end
            self.start_tangent = start_tangent # as 2d vector, from start point
            self.end_tangent = end_tangent # as 2d vector, from end point
            self.segments = segments

        def approximate(self):
            control_points = [
                self.start,
                vadd(self.start, self.start_tangent),
                vadd(self.end, self.end_tangent),
                self.end ]
            bezier = CubicBezierCurve(control_points)
            return bezier.approximate(self.segments)

    def __init__(self, color=const.BYLAYER, layer='0', linetype=None):
        self.color = color
        self.layer = layer
        self.linetype = linetype
        self.points = []

    def start(self, point, tangent):
        """Defines the start point and the start tangent.

        :param point: 2D start point
        :param tangent: start tangent as 2D vector, example: (5, 0) means a
            horizontal tangent with a length of 5 drawing units
        """
        self.points.append( (point, None, tangent, None) )

    def append(self, point, tangent1, tangent2=None, segments=20):
        """Append a control point with two control tangents.

        :param point: the control point as 2D point
        :param tangent1: first control tangent as 2D vector *left* of point
        :param tangent2: second control tangent as 2D vector *right* of point,
            if omitted tangent2 = -tangent1
        :param int segments: count of line segments for polyline approximation,
            count of line segments from previous control point to this point.
        """
        if tangent2 is None:
            tangent2 = (-tangent1[0], -tangent1[1])
        self.points.append( (point, tangent1, tangent2, int(segments)) )

    def _build_bezier_segments(self):
        if len(self.points) > 1:
            for from_point, to_point in zip(self.points[:-1], self.points[1:]):
                start_point = from_point[0]
                start_tangent = from_point[2] # tangent2
                end_point = to_point[0]
                end_tangent = to_point[1] # tangent1
                count = to_point[3]
                yield Bezier.Segment(start_point, end_point,
                                     start_tangent, end_tangent, count)
        else:
            raise ValueError('Tow or more points needed!')

    def _build_curve(self):
        polyline = Polyline(layer=self.layer, color=self.color,
                            linetype=self.linetype)
        for segment in self._build_bezier_segments():
            points = segment.approximate()
            polyline.add_vertices(points)
        return polyline

    def __dxf__(self):
        return self._build_curve().__dxf__()

class Spline(object):
    def __init__(self, points=[], segments=100, color=const.BYLAYER, layer='0',
                 linetype=None):
        self.color = color
        self.layer = layer
        self.linetype = linetype
        self.points = points
        self.segments = int(segments)

    def _build_curve(self):
        spline = CubicSpline(self.points)
        polyline = Polyline(spline.approximate(self.segments),
                            layer = self.layer,
                            color=self.color,
                            linetype = self.linetype)
        return polyline

    def __dxf__(self):
        return self._build_curve().__dxf__()

class Clothoid(object):
    def __init__(self, start=(0, 0), rotation=0., length=1., paramA=1.0,
                 mirrorx=False, mirrory=False, segments=100,
                 color=const.BYLAYER, layer='0', linetype=None):
        self.color = color
        self.layer = layer
        self.linetype = linetype
        self.start = start
        self.rotation = float(rotation)
        self.length = float(length)
        self.paramA = float(paramA)
        self.mirrorx = mirrorx
        self.mirrory = mirrory
        self.segments = int(segments)

    def _build_curve(self):
        def transform(points):
            for point in points:
                if self.mirrorx:
                    point = (point[0], -point[1])
                if self.mirrory:
                    point = (-point[0], point[1])
                point = rotate_2d(point, rotation)
                x, y = vadd(self.start, point)
                yield (x, y, zaxis)

        zaxis = 0. if len(self.start)<3 else self.start[2]
        rotation = radians(self.rotation)
        clothoid = _ClothoidValues(self.paramA)
        points = clothoid.approximate(self.length, self.segments)
        return Polyline(transform(points), color=self.color, layer=self.layer,
                        linetype=self.linetype)

    def __dxf__(self):
        return self._build_curve().__dxf__()
