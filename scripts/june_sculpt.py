"""June's reference sculpt: broad facial planes and swept, interlocking hair.

All detail is real geometry/vertex colour and follows the existing head bone.
Coordinates for the face are in the normalized anatomical source space;
hair is authored in head-local metres.
"""
import math
from mathutils import Vector


def sculpt_face(points):
    for p in points:
        if p.y < 5.45:
            continue
        x, y, z = p
        # Enlarge the complete eye socket, including the helper eyeball. The
        # surrounding temple and nose bridge get a smoothly diminishing move.
        eye = math.exp(-((abs(x)-.2885)/.245)**4-((y-6.795)/.24)**2)
        eye *= max(0, min(1, (z-.45)/.45))
        side = 1 if x >= 0 else -1
        p.x += (x-side*.2885)*.23*eye
        bridge=max(0,min(1,(abs(x)-.055)/.10))
        p.y += (y-6.795)*.80*eye*bridge
        # Full cheek planes taper into a shorter, softer lower face.
        p.x *= 1+.115*math.exp(-((y-6.56)/.43)**2)-.055*math.exp(-((y-5.98)/.22)**2)
        p.y += .10*math.exp(-((y-6.03)/.41)**2)
        # Give the smile corners a small upward turn without opening the lips.
        mouth = math.exp(-((abs(x)-.24)/.10)**2-((y-6.20)/.14)**2)
        p.y += .025*mouth*max(0, min(1, (z-.8)/.3))
        if p.y>7.15:
            p.y=7.15+(p.y-7.15)*.82


def hairline(angle):
    front = max(0, -math.cos(angle))
    rear = max(0, math.cos(angle))
    # A shallow widow's peak and lower temples, with an off-centre part.
    return 1.60+.38*rear**.8-.48*front**3+.08*front**14+.045*math.sin(angle)*front


def sculpt_hair(mesh, scalp):
    # Broad ribbons flow diagonally over the scalp. Their overlapping ridges
    # read as sculpted locks rather than equally spaced radial grooves.
    for lock in range(18):
        angle=math.tau*lock/18+.055*math.sin(lock*2.1)
        verts=[]; faces=[]
        for j in range(13):
            t=j/12
            twist=.46*math.sin(math.pi*t)*(-1 if math.sin(angle)<0 else 1)
            theta=angle+twist
            width=(.18+.025*math.sin(lock*1.8))*(1-.55*t)
            for k in range(7):
                cross=(k-3)/3
                a=theta+cross*width
                phi=hairline(a)*(1-t)+.19*t
                ridge=.001+(.004+.002*math.sin(lock*1.3))*(1-cross*cross)*math.sin(math.pi*(.08+.86*t))
                verts.append(scalp(a,phi,ridge))
        for j in range(12):
            for k in range(6):
                a=j*7+k; faces.append((a,a+7,a+8,a+1))
        mesh(verts,faces,'hairLight' if lock in (5,9,12) else 'hair','head')

    # A compact bun sits behind the crown. Six thick folded sections wrap
    # around its centre, giving it an irregular knot silhouette.
    center=Vector((.040,.293,-.007))
    vs=[center+Vector((0,.064,0))];fs=[];n=30;rows=18
    for j in range(1,rows):
        phi=math.pi*j/rows
        for i in range(n):
            a=i*math.tau/n
            r=1+.10*math.cos(5*a+1.8*phi)+.045*math.sin(3*a-phi)
            vs.append(center+Vector((.056*math.sin(phi)*math.cos(a)*r,.064*math.cos(phi),.055*math.sin(phi)*math.sin(a)*r)))
    for i in range(n):fs.append((0,1+(i+1)%n,1+i))
    for j in range(rows-2):
        for i in range(n):
            a=1+j*n+i;b=1+j*n+(i+1)%n;fs.append((a,b,b+n,a+n))
    bottom=len(vs);vs.append(center-Vector((0,.064,0)))
    for i in range(n):fs.append((bottom,1+(rows-2)*n+i,1+(rows-2)*n+(i+1)%n))
    mesh(vs,fs,'hair','head')
    for lock in range(7):
        vs=[];fs=[]
        for j in range(14):
            t=j/13;phi=.17+(math.pi-.30)*t
            theta=lock*math.tau/7+1.45*t
            for k in range(7):
                cross=(k-3)/3;a=theta+cross*.47
                r=1+.06*math.cos(5*a+1.8*phi)+.23*(1-cross*cross)
                vs.append(center+Vector((.058*math.sin(phi)*math.cos(a)*r,.063*math.cos(phi),.058*math.sin(phi)*math.sin(a)*r)))
        for j in range(13):
            for k in range(6):
                a=j*7+k;fs.append((a,a+1,a+8,a+7))
        mesh(vs,fs,'hairLight' if lock in (1,4) else 'hair','head')

    # Two unequal tapered locks frame the cheeks. A broad root curls into a
    # fine tip, matching the reference's swept-away fringe and loose wisps.
    for side in (-1,1):
        start=scalp(side*2.30,hairline(side*2.30)-.06,-.005)
        controls=[start,start+Vector((-.006,-.019,side*.007)),Vector((-.121,.153,side*.077)),
                  Vector((-.129,.117,side*.076)),Vector((-.133,.080,side*.067)),
                  Vector((-.122,.061,side*.063))]
        if side<0:
            controls[-2]+=Vector((.009,-.006,.004));controls[-1]+=Vector((.013,-.006,-.004))
        points=[]
        for j in range(len(controls)-1):
            a=controls[max(0,j-1)];b=controls[j];c=controls[j+1];d=controls[min(j+2,len(controls)-1)]
            for k in range(6):
                t=k/6
                points.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
        points.append(controls[-1]);vs=[];fs=[]
        for j,p in enumerate(points):
            t=j/(len(points)-1);width=.010*(1-t)**.8*(.35+.65*min(1,t/.10))+.00015
            tangent=(points[min(j+1,len(points)-1)]-points[max(0,j-1)]).normalized()
            across=tangent.cross(Vector((1,0,0))).normalized()
            depth=tangent.cross(across).normalized()
            for k in range(6):
                a=math.tau*k/6;vs.append(p+depth*(width*.44*math.cos(a))+across*(width*math.sin(a)))
        for j in range(len(points)-1):
            for k in range(6):
                a=j*6+k;b=j*6+(k+1)%6;fs.append((a,b,b+6,a+6))
        mesh(vs,[tuple(reversed(f)) for f in fs],'hair','head')


def garment_binding(verts, faces, colors, body_weights):
    """Thin bound cloth edges, carrying the same blended weights as the body."""
    from collections import defaultdict
    edges=defaultdict(list)
    normals=[Vector() for _ in verts]
    for face,color in zip(faces,colors):
        normal=(verts[face[1]]-verts[face[0]]).cross(verts[face[2]]-verts[face[0]])
        for i in face:normals[i]+=normal
        for a,b in zip(face,face[1:]+face[:1]):edges[tuple(sorted((a,b)))].append(color)
    adjacent=defaultdict(list)
    for (a,b),materials in edges.items():
        if any(c in materials for c in ('shirt','cream')) and ('skin' in materials or 'shorts' in materials):
            adjacent[a].append(b);adjacent[b].append(a)
    visited=set();out_verts=[];out_faces=[];out_weights=[]
    for first in adjacent:
        if first in visited:continue
        loop=[];current=first;previous=None
        while current not in visited:
            visited.add(current);loop.append(current)
            candidates=[i for i in adjacent[current] if i!=previous]
            if not candidates:break
            previous,current=current,candidates[0]
        if len(loop)<4:continue
        points=[verts[i].copy() for i in loop]
        offset=len(out_verts)
        for j,(i,p) in enumerate(zip(loop,points)):
            normal=normals[i].normalized()
            tangent=(points[(j+1)%len(points)]-points[(j-1)%len(points)]).normalized()
            across=tangent.cross(normal).normalized()
            for k in range(6):
                a=k*math.tau/6
                out_verts.append(p+normal*(.0006+.0010*math.cos(a))+across*(.0010*math.sin(a)))
                out_weights.append(body_weights[i])
        for j in range(len(loop)):
            for k in range(6):
                a=offset+j*6+k;b=offset+j*6+(k+1)%6
                c=offset+(j+1)%len(loop)*6+(k+1)%6;d=offset+(j+1)%len(loop)*6+k
                out_faces.append((a,b,c,d))
    return out_verts,out_faces,out_weights
