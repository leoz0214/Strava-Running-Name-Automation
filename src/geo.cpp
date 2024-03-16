// C++ module for comparing points with latitude/longitude stream,
// detecting if any or all points have been visited during the activity.
// Points are in the format [latitude, longitude, radius] stored contiguously.
// Lat/longs are in the format [latitude, longitude] also stored contiguously.
#include <cmath>


extern "C" {
    __declspec(dllexport) bool any_point_touched(
        double* points, double* lat_long_stream,
        unsigned point_count, unsigned lat_long_count);
    __declspec(dllexport) bool all_points_touched(
        double* points, double* lat_long_stream,
        unsigned point_count, unsigned lat_long_count);
};


const double EARTH_RADIUS = 6378.137;


// Returns the Haversine distance between two lat/long points in km.
inline double haversine_distance(
    double lat1, double long1, double lat2, double long2
) {
    double dlat = (lat2 - lat1) * M_PI / 180;
    double dlong = (long2 - long1) * M_PI / 180;
    lat1 *= M_PI / 180;
    lat2 *= M_PI / 180;
    double a = std::pow(std::sin(dlat / 2), 2) +
        std::cos(lat1) * std::cos(lat2) * std::pow(std::sin(dlong / 2), 2);
    return EARTH_RADIUS * 2 * std::asin(std::sqrt(a));
}


// Returns True if the point has been reached by at least 1 lat/long.
inline bool point_touched(
    double plat, double plong, double radius,
    double* lat_long_stream, unsigned lat_long_count
) {
    double radius_km = radius / 1000;
    for (int i = 0; i < lat_long_count; ++i) {
        if (
            haversine_distance(
                plat, plong, lat_long_stream[i*2], lat_long_stream[i*2+1])
            <= radius_km
        ) {
            return true;
        }
    }
    return false;
}


// Returns True if any point has been reached by a lat/long.
bool any_point_touched(
    double* points, double* lat_long_stream,
    unsigned point_count, unsigned lat_long_count
) {
    for (int i = 0; i < point_count; ++i) {
        if (
            point_touched(
                points[i*3], points[i*3+1], points[i*3+2],
                lat_long_stream, lat_long_count)
        ) {
            return true;
        }
    }
    return false;
}


// Returns True if ALL points have been reached by a lat/long.
bool all_points_touched(
    double* points, double* lat_long_stream,
    unsigned point_count, unsigned lat_long_count
) {
    for (int i = 0; i < point_count; ++i) {
        if (
            !point_touched(
                points[i*3], points[i*3+1], points[i*3+2],
                lat_long_stream, lat_long_count)
        ) {
            return false;
        }
    }
    return true;
}
