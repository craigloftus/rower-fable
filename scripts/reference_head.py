"""June's head authored from semantic planes in the reference turnaround.
Front coordinates are pixel landmarks, not a dense anatomical template.
Depths are read from the profile; details and silhouette stay independently editable.
"""
import math
from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt
from mathutils.bvhtree import BVHTree
S=.00056

def point(x,y,profile):
    depth=-.14+(profile-635)*S
    baseline=-.116+.063*(abs(x)/140)**3
    feature=(abs(x)<32 and 350<y<453) or (abs(x)<62 and 467<y<503)
    if not feature:depth=baseline+(depth-baseline)*.35
    return Vector((depth,.055+(560-y)*S,x*S))

def inside(p,poly):
    x,y=p;hit=False
    for a,b in zip(poly,poly[1:]+poly[:1]):
        if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:hit=not hit
    return hit

def build_head():
    vs=[];fs=[];mats=[]
    def mesh(points,faces,color):
        offset=len(vs);vs.extend(Vector(p) for p in points)
        fs.extend(tuple(offset+i for i in f) for f in faces);mats.extend([color]*len(faces))
    def sphere(center,scale,color,n=24,rings=12):
        points=[Vector(center)+Vector((0,scale[1],0))];faces=[]
        for j in range(1,rings):
            phi=math.pi*j/rings
            for i in range(n):
                a=math.tau*i/n
                points.append(Vector(center)+Vector((scale[0]*math.sin(phi)*math.cos(a),scale[1]*math.cos(phi),scale[2]*math.sin(phi)*math.sin(a))))
        for i in range(n):faces.append((0,1+(i+1)%n,1+i))
        for j in range(rings-2):
            for i in range(n):
                a=1+j*n+i;b=1+j*n+(i+1)%n;faces.append((a,b,b+n,a+n))
        bottom=len(points);points.append(Vector(center)-Vector((0,scale[1],0)))
        for i in range(n):faces.append((bottom,1+(rings-2)*n+i,1+(rings-2)*n+(i+1)%n))
        mesh(points,faces,color)
    landmarks=[];lookup={};edges=[]
    def landmark(x,y,depth):
        key=(x,y)
        if key not in lookup:
            lookup[key]=len(landmarks);landmarks.append((x,y,depth))
        return lookup[key]
    def chain(points,closed=False):
        ids=[landmark(*p) for p in points]
        edges.extend(zip(ids,ids[1:]+(ids[:1] if closed else [])))
        return ids
    outline=[(0,165,815),(85,180,805),(124,245,814),(137,320,835),(140,400,824),(117,476,795),(65,540,757),(0,560,706)]
    outline+= [(-x,y,d) for x,y,d in reversed(outline[1:-1])]
    boundary=chain(outline,True)
    for p in [(0,247,680),(0,300,685),(0,323,685),(0,370,663),(0,416,637),(0,433,635),(0,450,661),
              (0,466,665),(0,477,660),(0,485,663),(0,500,672),(0,522,688),(0,548,686)]:landmark(*p)
    for side in (-1,1):
        for x,y,d in [(70,250,700),(90,285,715),(20,300,684),(105,307,745),
                      (15,323,692),(16,368,682),(21,415,650),(18,434,645),(31,435,662),(21,446,663),
                      (33,395,689),(70,405,702),(99,393,745),(108,448,768),(65,457,710),
                      (43,458,687),(89,488,760),(60,521,746),(20,546,697)]:landmark(side*x,y,d)
        chain([(0,323,685),(side*16,368,682),(side*21,415,650),(side*31,435,662),(side*21,446,663),(0,450,661)])
    chain([(0,300,685),(0,323,685),(0,370,663),(0,416,637),(0,433,635),(0,450,661)])
    eye_paths=[];eye_centers=[];lid_ids=set()
    eye_shape=[(33,363),(43,349),(60,339),(81,340),(101,349),(110,360),(101,372),(80,378),(61,377),(42,373)]
    for side in (-1,1):
        center=Vector((-.089,.055+(560-359)*S,side*72*S));radii=Vector((.027,.023,.025))
        eye_centers.append((center,radii))
        shape=[(side*x,y) for x,y in eye_shape];eye_paths.append(shape)
        for ring in (0,1):
            points=[]
            for x,y in shape:
                dx=x-side*72;dy=y-359
                rx=dx*(1 if ring==0 else 1.17)+side*72
                ry=dy*(1 if ring==0 else 1.42)+359
                z=dx*S;yy=-dy*S
                depth=center.x-radii.x*math.sqrt(max(.03,1-(z/radii.z)**2-(yy/radii.y)**2))
                depth-=.0008 if ring==0 else .0016
                profile=635+(depth+.14)/S
                points.append((rx,ry,profile))
            ids=chain(points,True)
            if ring==0:lid_ids.update(ids)
    lip=[(-60,473,688),(-31,475,665),(-12,472,657),(0,477,660),(12,472,657),(31,475,665),(60,473,688),
         (45,489,684),(22,498,672),(0,500,672),(-22,498,672),(-45,489,684)]
    chain(lip,True)
    chain([(-60,473,688),(-28,482,671),(0,485,663),(28,482,671),(60,473,688)])
    coords,_,triangles,orig,_,_=delaunay_2d_cdt([Vector((x,y)) for x,y,d in landmarks],edges,[],0,1e-5)
    points=[]
    for xy,source_ids in zip(coords,orig):
        if source_ids:depth=landmarks[source_ids[0]][2]
        else:
            # Constraint intersections retain the depth of their source segment.
            candidates=[]
            for a,b in edges:
                pa=Vector(landmarks[a][:2]);pb=Vector(landmarks[b][:2]);delta=pb-pa
                t=max(0,min(1,(xy-pa).dot(delta)/delta.length_squared))
                candidates.append(((xy-pa.lerp(pb,t)).length,landmarks[a][2]*(1-t)+landmarks[b][2]*t))
            depth=min(candidates)[1]
        p=point(*xy,depth)
        if any(i in lid_ids for i in source_ids):p.x=-.14+(depth-635)*S
        points.append(p)
    face_polys=[];face_colors=[]
    for tri in triangles:
        xy=sum((coords[i] for i in tri),Vector((0,0)))/len(tri)
        if not inside(xy,[(x,y) for x,y,d in outline]) or any(inside(xy,path) for path in eye_paths):continue
        # Front normals face -X (front-image Y increases down the page).
        tri=tuple(tri)
        normal=(points[tri[1]]-points[tri[0]]).cross(points[tri[2]]-points[tri[0]])
        if normal.x>0:tri=tuple(reversed(tri))
        face_polys.append(tri)
        if inside(xy,[(x,y) for x,y,d in lip]):color='lipLower' if xy.y>484 else 'lipUpper'
        elif 375<xy.y<450 and 40<abs(xy.x)<115:color='cheek'
        else:color='skin'
        face_colors.append(color)
    offset=len(vs);vs.extend(points);fs.extend(tuple(offset+i for i in f) for f in face_polys);mats.extend(face_colors)
    # Three broad rear bands close the cranium behind the facial silhouette.
    front=[point(*p) for p in outline];back=[]
    for layer in range(3):
        t=layer/2
        for p in front:
            height=(p.y-.16)/.13
            x=.10-.055*min(1,abs(height))
            back.append(Vector((p.x if layer==0 else x,.17+(p.y-.17)*(1-.20*t),p.z*(1-.30*t))))
    rear_faces=[];n=len(front)
    for layer in range(2):
        for i in range(n):
            a=layer*n+i;b=layer*n+(i+1)%n;rear_faces.append((a,a+n,b+n,b))
    rear_faces.append(tuple(reversed(range(2*n,3*n))))
    mesh(back,rear_faces,'skin')
    surface=BVHTree.FromPolygons(points,face_polys)
    def face_point(x,y,lift=.0007):
        p=point(x,y,635)
        hit,normal,_,_=surface.ray_cast(Vector((-.5,p.y,p.z)),Vector((1,0,0)))
        return hit+normal*lift
    for side,(center,radii) in zip((-1,1),eye_centers):
        def eye_front(y,z,lift):
            r=1-((y-center.y)/radii.y)**2-((z-center.z)/radii.z)**2
            return Vector((center.x-radii.x*math.sqrt(max(0,r))-lift,y,z))
        white=[eye_front(center.y,center.z,0)]
        for ring in range(1,7):
            t=ring/6
            for x,y in eye_shape:
                white.append(eye_front(center.y-(y-359)*S*t,center.z+side*(x-72)*S*t,0))
        white_faces=[(0,1+i,1+(i+1)%10) for i in range(10)]
        for j in range(5):
            for i in range(10):
                a=1+j*10+i;b=1+j*10+(i+1)%10;white_faces.append((a,a+10,b+10,b))
        white_faces=[f if (white[f[1]]-white[f[0]]).cross(white[f[2]]-white[f[0]]).x<0 else tuple(reversed(f)) for f in white_faces]
        mesh(white,white_faces,'white')
        for radius,color,lift in [(.0118,'iris',.0003),(.0073,'pupil',.0005)]:
            eye_vs=[eye_front(center.y,center.z,lift)]
            for ring in range(1,7):
                for i in range(40):
                    a=i*math.tau/40;r=radius*ring/6
                    eye_vs.append(eye_front(center.y+r*math.sin(a),center.z+r*math.cos(a),lift))
            eye_fs=[(0,1+i,1+(i+1)%40) for i in range(40)]
            for j in range(5):
                for i in range(40):
                    a=1+j*40+i;b=1+j*40+(i+1)%40;eye_fs.append((a,a+40,b+40,b))
            mesh(eye_vs,eye_fs,color)
        sphere(eye_front(center.y+.004,center.z-.003,.0008),(.0005,.0018,.0018),'white',10,6)
        brow=[]
        for i in range(25):
            t=i/24;x=side*(28+83*t);y=302-6*math.sin(math.pi*t)+9*t*t
            width=6*(1-.80*t*t)
            for dy in (-width,width):brow.append(face_point(x,y+dy,.0016))
        mesh(brow,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(24)],'hairDark')
        # Eyelash ribbon along the actual authored upper-lid contour.
        lash=[]
        for x,y in eye_shape[:6]:
            for dy in (-2.3,0):lash.append(face_point(side*x,y+dy,.0010))
        mesh(lash,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(5)],'pupil')
    # Neck planes taper into the jaw; the lower ring is the rig attachment.
    neck=[];n=10
    for y,width,depth,cx in [(-.045,.048,.049,.015),(.012,.040,.043,.016),(.063,.047,.052,.008)]:
        for i in range(n):
            a=i*math.tau/n;neck.append((cx+depth*math.cos(a),y,width*math.sin(a)))
    mesh(neck,[(j*n+i,(j+1)*n+i,(j+1)*n+(i+1)%n,j*n+(i+1)%n) for j in range(2) for i in range(n)],'skin')
    # The ear is a folded rim surrounding a recessed bowl, not a sphere.
    for side in (-1,1):
        outline=[(-.018,.023,.010),(-.028,.009,.010),(-.022,-.014,.009),(-.010,-.027,.006),(.005,-.017,.012),(.009,.010,.016),(-.003,.027,.014)]
        center=Vector((-.002,.139,side*.084));ear=[]
        for t in (1,.58):
            for x,y,z in outline:ear.append(center+Vector((x*t,y*t,side*(z-.004*(1-t)))))
        ear.append(center+Vector((-.008,-.001,side*.004)))
        polys=[(i,(i+1)%7,(i+1)%7+7,i+7) for i in range(7)]+[(7+i,7+(i+1)%7,14) for i in range(7)]
        if side<0:polys=[tuple(reversed(p)) for p in polys]
        mesh(ear,polys[:7],'skin');mesh(ear,polys[7:],'earInner')
    # Four bands of broad hair planes follow the silhouette and sweep back.
    hair=[];n=18;rows=5
    for j in range(rows):
        t=j/(rows-1)
        for i in range(n):
            angle=math.tau*i/n
            front=max(0,math.cos(angle));rear=max(0,-math.cos(angle))
            edge_y=.145+.110*front**.7-.035*rear
            theta=angle+.32*math.sin(math.pi*t)*math.sin(angle)
            y=edge_y*(1-t)+.292*t+.010*math.sin(math.pi*t)*front
            x=(-.116*math.cos(theta)+.005)*(1-.86*t)+.008*t
            z=.091*math.sin(theta)*(1-.88*t)
            hair.append((x,y,z))
    hair_faces=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(rows-1) for i in range(n)]
    hair_faces.append(tuple(range((rows-1)*n,rows*n)))
    mesh(hair,[tuple(reversed(p)) for p in hair_faces],'hair')
    # An off-centre, flattened folded knot replaces the spherical bun.
    knot=[];polys=[];n=12;rings=7
    for j in range(rings+1):
        phi=math.pi*j/rings
        for i in range(n):
            a=math.tau*i/n+.24*math.sin(phi);r=1+.14*math.cos(3*a+2*phi)+.06*math.sin(5*a)
            x=.054*math.sin(phi)*math.cos(a)*r;y=.042*math.cos(phi);z=.066*math.sin(phi)*math.sin(a)*r
            knot.append((.052+x,.313+y*.96-z*.27,-.014+y*.27+z*.96))
    for j in range(rings):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;polys.append((a,b,b+n,a+n))
    mesh(knot,polys,'hair')
    for side in (-1,1):
        path=[(-.088,.239,side*.061),(-.103,.208,side*.069),(-.112,.169,side*.074),(-.121,.124,side*.069),(-.123,.096,side*.063),(-.118,.080,side*.060)]
        if side<0:path=path[:-1]
        strand=[]
        for j,p in enumerate(path):
            width=.009*(1-j/(len(path)-1))+.0002
            for k in range(4):
                a=math.tau*k/4;strand.append(Vector(p)+Vector((width*.36*math.cos(a),0,width*math.sin(a))))
        faces=[(j*4+k,j*4+(k+1)%4,(j+1)*4+(k+1)%4,(j+1)*4+k) for j in range(len(path)-1) for k in range(4)]
        mesh(strand,faces,'hair')
    return vs,fs,mats
