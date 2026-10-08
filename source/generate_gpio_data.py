#!/usr/bin/env python3
"""Generate CoreELEC's BL30 GPIO table from pinned local source trees."""

import argparse
from pathlib import Path
import re


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kernel", type=Path)
    parser.add_argument("bl30", type=Path)
    args = parser.parse_args()
    common = args.kernel / "common_drivers"
    cpu_defs = (common / "include/linux/amlogic/media/registers/cpu_version.h").read_text()
    paths = sorted(
        list((args.bl30 / "src_ao/demos/amlogic/n200/include").glob("*/gpio-data.h"))
        + list((args.bl30 / "rtos_sdk/soc/riscv").glob("*/gpio-data.h"))
    )
    if not paths:
        raise SystemExit("No BL30 GPIO headers found; check the source version/path")
    out = [
        "typedef struct bl30_gpio { char *name; uint32_t number; } bl30_gpio_t;\n",
        "typedef struct bl30_gpios_soc { enum meson_cpuid_type_e cpuid; "
        "bl30_gpio_t gpio[256]; } bl30_gpios_soc_t;\n",
        "bl30_gpios_soc_t bl30_gpios[] = {\n",
    ]
    for path in paths:
        macro = "MESON_CPU_MAJOR_ID_" + path.parent.name.upper()
        if macro not in cpu_defs:
            continue
        entries = re.findall(r"^#define\s+(GPIO\w+)\s+(\d+)", path.read_text(), re.M)
        if len(entries) > 256:
            raise SystemExit(f"Too many GPIO entries in {path}")
        out.append("  { " + macro + ", {\n")
        out.extend(f'    {{ "{name}", {number} }},\n' for name, number in entries)
        out.append("  }},\n")
    out.append("};\n")
    target = common / "drivers/bootloader/gpio_data.h"
    target.write_text("".join(out))
    print(f"Generated {target}")


if __name__ == "__main__":
    main()
