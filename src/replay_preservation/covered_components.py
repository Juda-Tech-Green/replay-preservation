"""Static component candidates within covered files; never certifies dependencies or executes."""
from pathlib import PurePosixPath
from .iso_coverage import FULL
from .signatures import classify

RULES = {
 'duke3d/buildhlp.exe':('embedded documentation viewer',b'Build for Duke Nukem 3D Help / Info',[],True),
 'duke3d/dn3dhelp.exe':('embedded documentation viewer',b'Duke Nukem Atomic v1.5 Technical Help',[],True),
 'duke3d/checkver.exe':('game-data version checker',b'Duke Nukem 3D GAME.CON file.', ['Duke3d/GAME.CON'],False),
 'quake/cwsdpmi.exe':('DOS DPMI runtime utility',b'CWSDPMI V0.90+',[],True),
 'tt_racing_class/class.exe':('release intro/demo candidate',b'Intro by ANIMAL',[],True),
 'vcop2/class.exe':('release-associated program; precise role unverified',b'PMODE/W v1.33',[],False),
 'vcop2/vc2.exe':('launcher with explicit external program references',b'PPJ2dd.exe',['VCOP2/CLASS.EXE','VCOP2/PPJ2DD.EXE'],False),
 'doom/dmaud.exe':('WAD audio editor',b'DOOM Audio Editor',['Doom/DOOM1.WAD'],False),
 'doom/dcc.exe':('DOOM game launcher',b'Choose External WAD Files',['Doom/DOOM.EXE','Doom/DOOM1.WAD'],False),
}


def inspect_components(files,read_payload):
    by_path={item['path'].casefold():item for item in files}
    results=[]
    for key,(role,marker,dependencies,single_file) in RULES.items():
        item=by_path.get(key)
        if not item or item['coverage_status']!=FULL:continue
        payload=read_payload(item)
        position=payload.find(marker)
        if position<0:continue
        dependency_rows=[]
        for name in dependencies:
            observed=by_path.get(name.casefold())
            dependency_rows.append({'path':name,'sector_covered':bool(observed and observed['coverage_status']==FULL),
                                    'evidence':'static reference or documented data role; not an exhaustive dependency proof'})
        results.append({'path':item['path'],'file_sha256':item['file_sha256'],
            'role':role,'classification':classify(payload,item['path']),
            'evidence_marker':marker.decode('ascii'),'marker_file_offset':position,
            'candidate_single_file_component':single_file,
            'observed_dependencies':dependency_rows,
            'observed_dependency_set_covered':all(row['sector_covered'] for row in dependency_rows),
            'required_file_manifest_established':False,'certified_self_contained':False,
            'game':False,'playable':False,'test_status':'not executed',
            'interpretation':'covered component candidate; external runtime/data requirements and internal integrity remain unverified'})
    return results
