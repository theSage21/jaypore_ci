from jaypore_ci.changelog import version_map

for version in sorted(version_map.keys(), reverse=True):
    print(version)
    print("-" * len(str(version)))
    print("")
    for line in version_map[version]["changes"]:
        print("-  ", line)
    print("")
