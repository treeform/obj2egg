""" by
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

from pandac.PandaModules import *
import math

def _float(i):
    try:
        return float(i)
    except:
        return 0

def floats(flaot_list):
    return [ _float(number) for number in flaot_list]

def _int(i):
    try:
        return int(i)
    except:
        return 0

def ints(int_list):
    return [ _int(number) for number in int_list]

def read_mtl(filename):
    textures = {}
    name = "default"
   
    file = open(filename)
    for line in file.readlines():
        if not line or "#" == line[0]:
            continue
        tokens = line.split()
        if tokens:
            if tokens[0] == "newmtl":
                name = tokens[1]
            elif tokens[0] == "map_Kd":
                textures[name] = tokens[1]
            else:
                print tokens
               
    print  textures
    return textures
                 
def read_obj(filename):
    file = open(filename)
    egg = EggData()
    meshName = ""
    textures = {}
    texture = None
    points = []
    uvs    = []
    normals= []
    faces  = []
    idx = 0
    for line in file.readlines()+['o']:
        line = line.strip()
        if not line or "#" == line[0]:
            continue
        tokens = line.split()
        if tokens:
            if tokens[0] == "v":   
                points.append(floats(tokens[1:]))
            elif tokens[0] == "vt": 
                uvs.append(floats(tokens[1:]))
            elif tokens[0] == "vn": 
                normals.append(floats(tokens[1:]))
            elif tokens[0] == "f":
                face = []
                for token in tokens[1:]:
                    face.append(ints(token.split("/")))
                faces.append(face)
            elif tokens[0] == "g" or tokens[0] == "o":
                if meshName != "":
                    egn = EggGroup(meshName)
                    egg.addChild(egn)
                    if texture and texture in textures:
                        et = EggTexture(texture,textures[texture])
                   
                    evp = EggVertexPool(meshName)
                    egn.addChild(evp)
                    for face in faces:
                        ep = EggPolygon()   
                        if et: ep.addTexture(et)               
                        for vertex in face:
                            if len(vertex) == 3:
                                iPoint, iUv, iNormal = vertex
                                ev = EggVertex()
                                point = points[iPoint-1]
                                ev.setPos(Point3D(point[0],point[1],point[2]))
                                ev.setUv(Point2D(*uvs[iUv-1][0:2]))
                                ev.setNormal(Vec3D(*normals[iNormal-1]))
                                evp.addVertex(ev)
                                ep.addVertex(ev)
                            else:
                                print vertex
                        egn.addChild(ep)
                if len(tokens) > 1 :
                    meshName = tokens[1] 
            elif tokens[0] == "mtllib":
                textures.update(read_mtl(tokens[1]))
            elif tokens[0] == "usemtl":
                texture = tokens[1]
            else:
                print tokens[0],"unkown"
   
    return egg


if __name__ == "__main__":
    import getopt
    import sys,os
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hn:bs", ["help","normals","binormals","show"])
    except getopt.error, msg:
        print msg
        print __doc__
        sys.exit(2)
    show = False
    for o, a in opts:
        if o in ("-h", "--help"):
            print __doc__
            sys.exit(0)
        elif o in ("-s", "--show"):
                show = True
    for infile in args:
        if ".obj" not in infile:
            print "WARNING",infile,"does not look like a valid obj file"
            continue
        egg = read_obj(infile)
        f, e = os.path.splitext(infile)
        outfile = f+".egg"
        for o, a in opts:
            if o in ("-n", "--normals"):
                egg.recomputeVertexNormals(float(a))
            elif o in ("-b", "--binormals"):
                egg.recomputeTangentBinormal(GlobPattern(""))
        egg.removeUnusedVertices(GlobPattern(""))
        egg.triangulatePolygons(EggData.TConvex & EggData.TPolygon)
        egg.writeEgg(Filename(outfile))
        if show:
            os.system("pview "+outfile) 
