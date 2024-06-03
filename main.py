if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import modules.processing as prc
    left_bottom = (39.395158, 52.491465)
    left_bottom_projected = prc.wgs84_point_to_crs(left_bottom, prc.MSK_48_CRS)
    right_top = (39.829939, 52.683001)
    right_top_projected = prc.wgs84_point_to_crs(right_top, prc.MSK_48_CRS)
    df_culled = prc.load_geojson('lipetsk_high.geojson', left_bottom, right_top)
    prc.validate_data(df_culled)
    df_projected = prc.project_geometry(df_culled, prc.MSK_48_CRS)    
    fig, axes = plt.subplots(2, 2)
    
    df_culled.plot(column='elevation', ax=axes[0][0], legend=True)
    df_projected.plot(column='elevation', ax=axes[0][1], legend=True)
    axes[1][0].set_xlim(left_bottom[0], right_top[0])
    axes[1][0].set_ylim(left_bottom[1], right_top[1])
    axes[1][1].set_xlim(left_bottom_projected[0], right_top_projected[0])
    axes[1][1].set_ylim(left_bottom_projected[1], right_top_projected[1])
    df_culled.plot(column='elevation', ax=axes[1][0], legend=True)
    df_projected.plot(column='elevation', ax=axes[1][1], legend=True)
    plt.show()