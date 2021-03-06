import pkg_resources
import pathlib
import json
import pandas as pd
import xarray as xr


IAGOS_REGIONS = {
    'WNAm': ('western North America', [-125, -105], [40, 60]),
    'EUS': ('the eastern United States', [-90, -60], [35, 50]),
    'NAt': ('the North Atlantic', [-50, -20], [50, 60]),
    'Eur': ('Europe', [-15, 15], [45, 55]),
    'WMed': ('the western Mediterranean basin', [-5, 15], [35, 45]),
    'MidE': ('the Middle East', [25, 55], [35, 45]),
    'Sib': ('Siberia', [40, 120], [50, 65]),
    'NEAs': ('the northeastern Asia', [105, 145], [30, 50]),
}


if __name__ == '__main__':
    data_path = pathlib.Path(pkg_resources.resource_filename('data_access', 'resources/iagos_L3_postprocessed'))
    md = []
    for url in data_path.glob('*/*.nc'):
        rel_url = url.relative_to(data_path)
        with xr.open_dataset(url) as ds:
            ds_md = {
                'title': ds.attrs['title'],
                'urls': str(rel_url),
            }

            if 'CO_mean' in ds:
                v = 'Carbon Monoxide'
            elif 'O3_mean' in ds:
                v = 'Ozone'
            else:
                continue
            ds_md['ecv_variables'] = [v]

            t0, t1 = ds.time.min(), ds.time.max()
            time_fmt = '%Y-%m-%dT%H:%M:%SZ'
            ds_md['time_period'] = [pd.Timestamp(t.values, tz='UTC').strftime(time_fmt) for t in (t0, t1)]

            ds_md['RI'] = 'IAGOS'

            ds_md['vars'] = list(ds)
            ds_md['layer'] = list(ds.layer.values.tolist())

            if 'IATA_code' in ds.attrs:
                ds_md['platform_id'] = ds.attrs['IATA_code']
                for k in ['longitude', 'latitude']:
                    ds_md[k] = ds.attrs[k]
            elif 'region_code' in ds.attrs:
                region_code = ds.attrs['region_code']
                ds_md['platform_id'] = region_code
                _, region_lon, region_lat = IAGOS_REGIONS[region_code]
                ds_md['longitude'] = 0.5 * sum(region_lon)
                ds_md['latitude'] = 0.5 * sum(region_lat)

        md.append(ds_md)

    catalogue_url = pkg_resources.resource_filename('data_access', 'resources/catalogue.json')
    with open(catalogue_url, 'w') as f:
        json.dump(md, f, indent=2)
