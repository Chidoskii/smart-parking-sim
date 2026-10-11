"""Convert SUMO parkingArea definitions to georeferenced label points.
Usage: python generate_parking_areas.py parking.add.xml osm.net.xml.gz parking-areas.geojson
Requires: pip install pyproj
"""
import argparse, gzip, json, math, xml.etree.ElementTree as ET
from pathlib import Path
from pyproj import CRS, Transformer

def open_xml(path):
    return gzip.open(path, 'rb') if str(path).endswith('.gz') else open(path, 'rb')

def interpolate(shape, distance):
    lengths = [math.dist(a,b) for a,b in zip(shape,shape[1:])]
    remaining = max(0, min(distance, sum(lengths)))
    for (ax,ay),(bx,by),length in zip(shape,shape[1:],lengths):
        if length and remaining <= length:
            t = remaining/length
            return (ax+t*(bx-ax), ay+t*(by-ay)), ((bx-ax)/length,(by-ay)/length)
        remaining -= length
    ax,ay=shape[-2]; bx,by=shape[-1]
    length=math.hypot(bx-ax,by-ay)
    return (bx,by), ((bx-ax)/length,(by-ay)/length)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('parking_xml')
    parser.add_argument('network_xml')
    parser.add_argument('output')
    args=parser.parse_args()
    with open_xml(args.network_xml) as f:
        root=ET.parse(f).getroot()
    location=root.find('location')
    offset_x,offset_y=map(float,location.attrib['netOffset'].split(','))
    transformer=Transformer.from_crs(CRS.from_user_input(location.attrib['projParameter']),CRS.from_epsg(4326),always_xy=True)
    lanes={}
    for lane in root.iter('lane'):
        if lane.get('id') and lane.get('shape'):
            lanes[lane.get('id')]=(float(lane.get('length','0')),[(float(x),float(y)) for x,y in (p.split(',') for p in lane.get('shape').split())])
    with open_xml(args.parking_xml) as f:
        areas=ET.parse(f).getroot().findall('parkingArea')
    features=[]; missing=[]
    for area in areas:
        area_id=area.get('id'); lane_id=area.get('lane')
        if lane_id not in lanes or len(lanes[lane_id][1])<2:
            missing.append((area_id,lane_id)); continue
        lane_length,shape=lanes[lane_id]
        start=float(area.get('startPos','0'))
        end=float(area.get('endPos',str(lane_length)))
        if start < 0: start+=lane_length
        if end < 0: end+=lane_length
        mid=(max(0,min(lane_length,start))+max(0,min(lane_length,end)))/2
        # SUMO lane length and polyline length can differ slightly; scale longitudinal position.
        geometric_length=sum(math.dist(a,b) for a,b in zip(shape,shape[1:]))
        (x,y),(dx,dy)=interpolate(shape,mid*geometric_length/lane_length if lane_length else 0)
        left=area.get('lefthand')=='1'
        side=1 if left else -1
        # A modest side offset helps distinguish parking rows sharing the same lane.
        offset=3.0
        x+=side*(-dy)*offset; y+=side*dx*offset
        lon,lat=transformer.transform(x-offset_x,y-offset_y)
        features.append({'type':'Feature','properties':{
            'id':area_id,'lane':lane_id,'campusLot':None,
            'roadsideCapacity':int(area.get('roadsideCapacity','0')),
            'explicitSpaceCount':len(area.findall('space')),
            'lefthand':left,'startPos':start,'endPos':end
        },'geometry':{'type':'Point','coordinates':[round(lon,8),round(lat,8)]}})
    result={'type':'FeatureCollection','features':features}
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(f'Parking areas: {len(areas)}; exported: {len(features)}; missing lanes: {len(missing)}')
    if missing: print('Missing:',missing)
    print('Saved:',args.output)

if __name__=='__main__': main()
