#!/usr/bin/python
"""
	This Version: $Id: obj2egg.py,v 1.7 2008/05/26 17:42:53 andyp Exp $
	Info: info >at< pfastergames.com

	Extended from: http://panda3d.org/phpbb2/viewtopic.php?t=3378
	.___..__ .___.___.___.__..__ .  .
	  |  [__)[__ [__ [__ |  |[__)|\/|
	  |  |  \[___[___|   |__||  \|  |
	obj2egg.py [n##][b][t][s] filename1.obj ...
		-n regenerate normals with # degree smoothing
			exaple -n30  (normals at less 30 degrees will be smoothed)
		-b make binarmals
		-t make tangents
		-s show in pview

	licensed under WTFPL (http://sam.zoy.org/wtfpl/)
"""

from panda3d.core import *
from panda3d.egg import *

import math
import string
import getopt
import sys, os


def floats(float_list):
	"""coerce a list of strings that represent floats into a list of floats"""
	return [ float(number) for number in float_list ]

def ints(int_list):
	"""coerce a list of strings that represent integers into a list of integers"""
	return [ int(number) for number in int_list ]


class ObjMaterial:
	"""a wavefront material"""
	def __init__(self):
		self.filename = None
		self.name = "default"
		self.eggdiffusetexture = None
		self.eggmaterial = None
		self.attrib = {}
		self.attrib["Ns"] = 100.0
		self.attrib["d"] = 1.0
		self.attrib["illum"] = 2
		# "magenta"
		self.attrib["Kd"] = [1.0, 0.0, 1.0]
		self.attrib["Ka"] = [0.0, 0.0, 0.0]
		self.attrib["Ks"] = [0.0, 0.0, 0.0]
		self.attrib["Ke"] = [0.0, 0.0, 0.0]

	def put(self, key, value):
		self.attrib[key] = value
		return self

	def get(self, key):
		return self.attrib[key] if key in self.attrib else None

	def has_key(self, key):
		return key in self.attrib

	def isTextured(self):
		return "map_Kd" in self.attrib

	def getEggTexture(self):
		if self.eggdiffusetexture:
			return self.eggdiffusetexture
		if not self.isTextured():
			return None
		m = EggTexture(self.name + "_diffuse", self.get("map_Kd"))
		m.setFormat(EggTexture.FRgb)
		m.setMagfilter(EggTexture.FTLinearMipmapLinear)
		m.setMinfilter(EggTexture.FTLinearMipmapLinear)
		m.setWrapU(EggTexture.WMRepeat)
		m.setWrapV(EggTexture.WMRepeat)
		self.eggdiffusetexture = m
		return self.eggdiffusetexture

	def getEggMaterial(self):
		if self.eggmaterial:
			return self.eggmaterial
		m = EggMaterial(self.name + "_mat")
		# XXX TODO: add support for specular, and obey illum setting
		# XXX as best as we can
		
		for key in ["Kd", "Ka", "Ks"]:
			with self.get(key) as rgb:
				if rgb is not None: {"Kd":m.setDiff, "Ka":m.setAmb, "Ks":m.setSpec}[key](Vec4(rgb[0], rgb[1], rgb[2], 1.0))
		
		ns = self.get("Ns")
		if ns is not None:
			m.setShininess(ns)
		
		self.eggmaterial = m
		return self.eggmaterial

class MtlFile:
	"""an object representing all Wavefront materials in a .mtl file"""
	def __init__(self, filename=None):
		self.filename = None
		self.materials = {}
		self.comments = {}
		if filename is not None:
			self.read(filename)

	def read(self, filename, verbose=False):
		self.filename = filename
		self.materials = {}
		self.comments = {}
		
		with open(filename) as open_file:
			linenumber = 0
			mat = None
			for line in open_file.readlines():
				line = line.strip()
				linenumber = linenumber + 1
				if not line:
					continue
				if line[0] == '#':
					self.comments[linenumber] = line
					print(line)
					continue
				tokens = line.split()
				if not tokens:
					continue
				if verbose: print("tokens[0]:", tokens)
				if tokens[0] == "newmtl":
					mat = ObjMaterial()
					mat.filename = filename
					mat.name = tokens[1]
					self.materials[mat.name] = mat
					if verbose: print("newmtl:", mat.name)
					continue
				if tokens[0] in ("Ns", "d", "Tr"):
					mat.put(tokens[0], float(tokens[1]))
					continue
				if tokens[0] in ("illum"):
					mat.put(tokens[0], int(tokens[1]))
					continue
				if tokens[0] in ("Kd", "Ka", "Ks", "Ke"):
					mat.put(tokens[0], floats(tokens[1:]))
					continue
				if tokens[0] in ("map_Kd", "map_Bump", "map_Ks", "map_bump", "bump"):
					mat.put(tokens[0], pathify(tokens[1]))
					if verbose: print("map:", mat.name, tokens[0], mat.get(tokens[0]))
					continue
				if tokens[0] in ("Ni"):
					mat.put(tokens[0], float(tokens[1]))
					continue
				print("file \"%s\": line %d: unrecognized:" % (filename, linenumber), tokens)
		
		if verbose: print("%d materials" % len(self.materials), "loaded from", filename)
		return self

class ObjFile:
	"""a representation of a wavefront .obj file"""
	def __init__(self, filename=None):
		self.filename = None
		self.objects = ["defaultobject"]
		self.groups = ["defaultgroup"]
		self.points = []
		self.uvs = []
		self.normals = []
		self.faces = []
		self.polylines = []
		self.matlibs = []
		self.materialsbyname = {}
		self.comments = {}
		self.currentobject = self.objects[0]
		self.currentgroup = self.groups[0]
		self.currentmaterial = None
		if filename is not None:
			self.read(filename)

	def read(self, filename, verbose=False):
		if verbose: print("ObjFile.read:", "filename:", filename)
		self.filename = filename
		self.objects = ["defaultobject"]
		self.groups = ["defaultgroup"]
		self.points = []
		self.uvs = []
		self.normals = []
		self.faces = []
		self.polylines = []
		self.matlibs = []
		self.materialsbyname = {}
		self.comments = {}
		self.currentobject = self.objects[0]
		self.currentgroup = self.groups[0]
		self.currentmaterial = None
		
		with open(filename) as open_file:
			linenumber = 0
			for line in open_file.readlines():
				line = line.strip()
				linenumber = linenumber + 1
				if not line:
					continue
				if line[0] == '#':
					self.comments[linenumber] = line
					print(line)
					continue
				tokens = line.split()
				if not tokens:
					continue
				
				commands = 	{
							"mtllib":	[self.__mtllib, 		tokens[1]],
							"g":		[self.__newgroup, 		"".join(tokens[1:])], 
							"o":		[self.__newobject, 		"".join(tokens[1:])], 
							"usemtl":	[self.__usematerial, 	tokens[1]], 
							"v":		[self.__newv, 			tokens[1:]], 
							"vn":		[self.__newnormal, 		tokens[1:]], 
							"vt":		[self.__newuv, 			tokens[1:]], 
							"f":		[self.__newface, 		tokens[1:]], 
							"l":		[self.__newpolyline, 	tokens[1:]]}
				
				if tokens[0] in commands:
					if verbose: print(tokens[0]+":", tokens[1:])
					commands[tokens[0]][0](commands[tokens[0]][1])
					continue
				
				if tokens[0] == "s":
					# apparently, this enables/disables smoothing
					print("%s:%d:" % (filename, linenumber), "ignoring:", tokens)
					continue
				print("%s:%d:" % (filename, linenumber), "unknown:", tokens)
		return self

	def __vertlist(self, lst):
		res = []
		for vert in lst:
			vinfo = vert.split("/")
			
			vertex = {'v':None, 'vt':None, 'vn':None}
			if len(vinfo) in [1,2,3]:
				for i in range(min(len(vinfo),3)):
					vertex[['v','vt','vn'][i]] = int(vinfo[i]) if not vinfo[i] == '' else None
			else:
				print("aborting...")
				raise(UNKNOWN, res)
			
			res.append(vertex)
		return res
	
	def __mtllib(self, mtl):
		mtllib = MtlFile(mtl)
		self.matlibs.append(mtllib)
		self.indexmaterials(mtllib)
		return self
	
	def __enclose(self, lst):
		mdata = (self.currentobject, self.currentgroup, self.currentmaterial)
		return (lst, mdata)

	def __newpolyline(self, l):
		polyline = self.__vertlist(l)
		self.polylines.append(self.__enclose(polyline))
		return self

	def __newface(self, f):
		face = self.__vertlist(f)
		self.faces.append(self.__enclose(face))
		return self

	def __newuv(self, uv):
		self.uvs.append(floats(uv))
		return self

	def __newnormal(self, normal):
		self.normals.append(floats(normal))
		return self

	def __newv(self, v):
		# capture the current metadata with vertices
		vdata = floats(v)
		mdata = (self.currentobject, self.currentgroup, self.currentmaterial)
		vinfo = (vdata, mdata)
		self.points.append(vinfo)
		return self

	def indexmaterials(self, mtllib, verbose=False):
		# traverse the materials defined in mtllib, indexing
		# them by name.
		for mname in mtllib.materials:
			mobj = mtllib.materials[mname]
			self.materialsbyname[mobj.name] = mobj
		if verbose: 
			print("indexmaterials:", mtllib.filename, "materials:", self.materialsbyname.keys())
		return self

	def __closeobject(self):
		self.currentobject = "defaultobject"
		return self

	def __newobject(self, object):
		self.__closeobject()
		self.currentobject = object
		self.objects.append(object)
		return self

	def __closegroup(self):
		self.currentgroup = "defaultgroup"
		return self

	def __newgroup(self, group):
		self.__closegroup()
		self.currentgroup = group
		self.groups.append(group)
		return self

	def __usematerial(self, material):
		if material in self.materialsbyname:
			self.currentmaterial = material
		else:
			print("warning:", "__usematerial:", "unknown material:", material)
		return self

	def __itemsby(self, itemlist, objname, groupname):
		res = []
		for item in itemlist:
			vlist, mdata = item
			wobj, wgrp, wmat = mdata
			if (wobj == objname) and (wgrp == groupname):
				res.append(item)
		return res

	def __facesby(self, objname, groupname):
		return self.__itemsby(self.faces, objname, groupname)

	def __linesby(self, objname, groupname):
		return self.__itemsby(self.polylines, objname, groupname)

	def __eggifyverts(self, eprim, evpool, vlist):
		for vertex in vlist:
			ixyz = vertex['v']
			vinfo = self.points[ixyz-1]
			vxyz, vmeta = vinfo
			ev = EggVertex()
			ev.setPos(Point3D(vxyz[0], vxyz[1], vxyz[2]))
			iuv = vertex['vt']
			if iuv is not None:
				vuv = self.uvs[iuv-1]
				ev.setUv(Point2D(vuv[0], vuv[1]))
			inormal = vertex['vn']
			if inormal is not None:
				vn = self.normals[inormal-1]
				ev.setNormal(Vec3D(vn[0], vn[1], vn[2]))
			evpool.addVertex(ev)
			eprim.addVertex(ev)
		return self

	def __eggifymats(self, eprim, wmat):
		if wmat in self.materialsbyname:
			mtl = self.materialsbyname[wmat]
			if mtl.isTextured():
				eprim.setTexture(mtl.getEggTexture())
				# NOTE: it looks like you almost always want to setMaterial()
				#       for textured polys.... [continued below...]
				eprim.setMaterial(mtl.getEggMaterial())
			rgb = mtl.get("Kd")
			if rgb is not None:
				# ... and some untextured .obj's store the color of the
				# material # in the Kd settings...
				eprim.setColor(Vec4(rgb[0], rgb[1], rgb[2], 1.0))
			# [continued...] but you may *not* always want to assign
			# materials to untextured polys...  hmmmm.
		return self

	def __facestoegg(self, egg, objname, groupname):
		selectedfaces = self.__facesby(objname, groupname)
		if len(selectedfaces) == 0:
			return self
		eobj = EggGroup(objname)
		egg.addChild(eobj)
		egrp = EggGroup(groupname)
		eobj.addChild(egrp)
		evpool = EggVertexPool(groupname)
		egrp.addChild(evpool)
		for face in selectedfaces:
			vlist, mdata = face
			wobj, wgrp, wmat = mdata
			epoly = EggPolygon()
			egrp.addChild(epoly)
			self.__eggifymats(epoly, wmat)
			self.__eggifyverts(epoly, evpool, vlist)
		#; each matching face
		return self

	def __polylinestoegg(self, egg, objname, groupname):
		selectedlines = self.__linesby(objname, groupname)
		if len(selectedlines) == 0:
			return self
		eobj = EggGroup(objname)
		egg.addChild(eobj)
		egrp = EggGroup(groupname)
		eobj.addChild(egrp)
		evpool = EggVertexPool(groupname)
		egrp.addChild(evpool)
		for line in selectedlines:
			vlist, mdata = line
			wobj, wgrp, wmat = mdata
			eline = EggLine()
			egrp.addChild(eline)
			self.__eggifymats(eline, wmat)
			self.__eggifyverts(eline, evpool, vlist)
		#; each matching line
		return self

	def toEgg(self, verbose=True):
		if verbose: print("converting...")
		# make a new egg
		egg = EggData()
		# convert polygon faces
		if len(self.faces) > 0:
			for objname in self.objects:
				for groupname in self.groups:
					self.__facestoegg(egg, objname, groupname)
		# convert polylines
		if len(self.polylines) > 0:
			for objname in self.objects:
				for groupname in self.groups:
					self.__polylinestoegg(egg, objname, groupname)
		return egg

def pathify(path):
	if os.path.isfile(path):
		return path
	# if it was written on win32, it may have \'s in it, and
	# also a full rather than relative pathname (Hexagon does this... ick)
	orig = path
	path = path.lower()
	path = path.replace("\\", "/")
	h, t = os.path.split(path)
	if os.path.isfile(t):
		return t
	print("warning: can't make sense of this map file name:", orig)
	return t
	
def main(argv=None):
	if argv is None:
		argv = sys.argv
	try:
		opts, args = getopt.getopt(argv[1:], "hn:bs", ["help", "normals", "binormals", "show"])
	except getopt.error as msg:
		print(msg)
		print(__doc__)
		return 2
	show = False
	for o, a in opts:
		if o in ("-h", "--help"):
			print(__doc__)
			return 0
		elif o in ("-s", "--show"):
			show = True
	for infile in args:
		try:
			if ".obj" not in infile:
				print("WARNING", finfile, "does not look like a valid obj file")
				continue
			obj = ObjFile(infile)
			egg = obj.toEgg()
			f, e = os.path.splitext(infile)
			outfile = f + ".egg"
			for o, a in opts:
				if o in ("-n", "--normals"):
					egg.recomputeVertexNormals(float(a))
				elif o in ("-b", "--binormals"):
					egg.recomputeTangentBinormal(GlobPattern(""))
			egg.removeUnusedVertices(GlobPattern(""))
			if True:
				egg.triangulatePolygons(EggData.TConvex & EggData.TPolygon)
			if True:
				egg.recomputePolygonNormals()
			egg.writeEgg(Filename(outfile))
			if show:
				os.system("pview " + outfile)
		except Exception as e:
			print(e)
	return 0

if __name__ == "__main__":
	sys.exit(main())


