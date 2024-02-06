import webbrowser

import folium
import geopandas as gpd
import numpy as np
import overpy
import time
import pickle
from overpy.exception import OverpassTooManyRequests, OverpassGatewayTimeout
from shapely.geometry.polygon import Polygon


class AreaBoundingBox:
    def __init__(self, longitude_west: float, longitude_east: float, latitude_south: float, latitude_north: float):
        self.longitude_west: float = longitude_west
        self.longitude_east: float = longitude_east
        self.latitude_south: float = latitude_south
        self.latitude_north: float = latitude_north

    def __str__(self):  # should be "(lat_south,long_west,lat_north,long_east)"
        return f"({self.latitude_south},{self.longitude_west},{self.latitude_north},{self.longitude_east})"


def save_results(filename: str, results):
    with open(filename, 'wb') as f:
        pickle.dump(results, f, pickle.HIGHEST_PROTOCOL)


def load_results(filename: str):
    with open(filename, 'rb') as f:
        results = pickle.load(f)
    return results


def execute_API_query(query: str) -> object:
    api = overpy.Overpass()
    while True:
        try:
            results = api.query(query)
        except OverpassTooManyRequests:
            time.sleep(1)
            print('Retrying...')
            continue
        except OverpassGatewayTimeout:
            time.sleep(10)
            print('OverpassGatewayTimeout, retrying...')
            continue
        break
    return results


def get_nodes_in_route(result: object) -> object:
    for single_way in result.get_ways():
        while True:
            try:
                single_way.get_nodes(resolve_missing=True)
            except OverpassTooManyRequests:
                time.sleep(1)
                print('Retrying...')
                continue
            except OverpassGatewayTimeout:
                time.sleep(10)
                print('OverpassGatewayTimeout, retrying...')
                continue
            break
    return result


def get_bicycle_ways(region: AreaBoundingBox) -> object:
    query_string = f"[out:json];" \
                   f"(relation[route=bicycle]{region};" \
                   f"way[highway=cycleway]{region};" \
                   f"way[highway=path][bicycle=designated]{region};);" \
                   f"out body;"
    result = execute_API_query(query_string)

    result = get_nodes_in_route(result)

    return result


def get_car_ways(region: AreaBoundingBox) -> object:
    query_string = f"""[out:json];
(way['highway'='primary']{region};
way['highway'='secondary']{region};
way['highway'='tertiary']{region};
way['highway'='unclassified']{region};
way['highway'='residential']{region};);
out body;   
"""

    result = execute_API_query(query_string)
    result = get_nodes_in_route(result)
    return result


def draw_results_on_map(region: AreaBoundingBox, result):
    bbox_polygon = Polygon(np.array([
        [region.longitude_east, region.latitude_south],
        [region.longitude_east, region.latitude_north],
        [region.longitude_west, region.latitude_north],
        [region.longitude_west, region.latitude_south]
    ]))

    m = folium.Map(location=[0.5 * (region.latitude_south + region.latitude_north),
                             0.5 * (region.longitude_east + region.longitude_west)], zoom_start=15,
                   tiles="CartoDB Positron")

    folium.GeoJson(data=gpd.GeoSeries(bbox_polygon).to_json(),
                   style_function=lambda x: {'fillColor': 'red'}).add_to(m)

    way_dict = {}

    for single_way in result.ways:
        node_list = []
        for node in single_way.nodes:
            node_list.append([float(node.lat), float(node.lon)])
        way_dict[single_way.id] = np.array(node_list)

    for id, way in way_dict.items():
        for node in way:
            folium.CircleMarker([node[0], node[1]], radius=1, fill_color='red').add_to(m)

        for i in range(len(way) - 1):
            folium.PolyLine([[way[i][0], way[i][1]], [way[i + 1][0], way[i + 1][1]]]).add_to(m)

    file_name = 'test_map.html'
    m.save(file_name)
    webbrowser.open(file_name)


test = AreaBoundingBox(19.98687, 19.9903, 50.0885, 50.0904)
# ways = get_bicycle_ways(test)
# ways = get_car_ways(test)
# save_results("testCar.pkl", ways)

new_results = load_results('testCar.pkl')

draw_results_on_map(test, new_results)
pass
