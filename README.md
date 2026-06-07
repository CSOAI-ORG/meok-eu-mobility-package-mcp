<!-- mcp-name: io.github.CSOAI-ORG/meok-eu-mobility-package-mcp -->
[![MCP Scorecard: 90/100](https://img.shields.io/badge/proofof.ai-90%2F100-5b21b6)](https://proofof.ai/scorecard/meok-eu-mobility-package-mcp.html)

# meok-eu-mobility-package-mcp

> EU Mobility Package compliance for cross-border road transport. 27 member states + UK/EFTA/EEA. EU 561/2006, Posted Workers Directive, IMI declarations, Smart Tachograph 2 v2, cabotage 3-in-7, return-to-base. By **MEOK AI Labs**.

## Why this exists

The EU Mobility Package (2020-2026 phased) is the biggest road-transport regulatory overhaul since 1969. Operators running cross-border face:

- **EU 561/2006** drivers' hours (still binding post-Brexit for UK→EU)
- **Directive (EU) 2020/1057** — Posted Workers applied to mobile workers
- **IMI declarations** mandatory for cabotage + cross-trade
- **Smart Tacho 2 v2** retrofit by 1 July 2026 for 2.5-3.5t vans
- **3-in-7 cabotage** with 4-day cooling-off
- **4-week return-to-base** for drivers
- **8-week return-to-base** for vehicles

Member-state enforcement is aggressive: France €15k/op, Germany €5k/op, Belgium drug-test roadside checks. UK-EU operators are particularly exposed.

## Install

```bash
pip install meok-eu-mobility-package-mcp
```

## Tools (9)

| Tool | Use case |
|------|----------|
| `check_drivers_hours_eu` | EU 561/2006 weekly audit |
| `check_return_to_base_4w` | Driver 4-week return |
| `check_vehicle_return_to_base_8w` | Vehicle 8-week return |
| `check_cabotage_3in7` | 3 ops / 7 days after intl unload |
| `check_smart_tachograph_2_v2` | G2V2 retrofit (1 Jul 2026 cliff) |
| `check_imi_posted_worker_declaration` | Posted Workers in road transport |
| `check_working_time_directive` | Dir 2002/15/EC 48h/week cap |
| `generate_eu_compliance_pack` | Cross-border audit pack |
| `check_eu_aetr_third_country` | AETR for non-EU routes (TR/UA/RU+) |

## Pricing

- **Free** — MIT self-host
- **Starter** — €49/mo
- **Pro** — €149/mo (multi-driver, multi-MS)
- **Fleet** — €799/mo (50+ vehicles, cross-border evidence pack)
- **Enterprise** — €1,999/mo (named CSM + SLA + member-state-specific)

## Regulatory basis

- Regulation (EC) 561/2006 — drivers' hours
- Regulation (EU) 165/2014 + Implementing Reg 2021/1228 — Smart Tacho 2
- Directive 2002/15/EC — Working Time
- Directive (EU) 2020/1057 — Posted Workers in road transport
- Regulation (EU) 2020/1054 — Mobility Package I (driver return)
- Regulation (EU) 2020/1055 — Mobility Package I (access + cabotage)
- AETR (European Agreement Concerning the Work of Crews)

## License

MIT © 2026 Nicholas Templeman / MEOK AI Labs · [haulage.app](https://haulage.app)


## Configuration

Add to your `claude_desktop_config.json` (Claude Desktop) or your MCP client config:

```json
{
  "mcpServers": {
    "meok-eu-mobility-package-mcp": {
      "command": "uvx",
      "args": ["meok-eu-mobility-package-mcp"]
    }
  }
}
```

Or: `pip install meok-eu-mobility-package-mcp` then run the `meok-eu-mobility-package-mcp` command (stdio transport).

## Examples

Once configured, ask your assistant, for example:
- "Use `check_drivers_hours_eu` to …"
- "Use `check_return_to_base_4w` to …"
- "Use `check_vehicle_return_to_base_8w` to …"


<!-- GEO-FOOTER:v1 -->

---

### Part of the MEOK constellation

This MCP is one node in a connected ecosystem built by **MEOK AI LABS** around a single
sovereign AI core — governed agents with a hash-chained audit trail, mapped to the CSOAI
compliance charter.

- 🌐 The whole map: **<https://meok.ai/constellation>**
- 🛡️ AI governance & certification: **<https://councilof.ai>** · **<https://csoai.org>**
- ✅ Verify any signed report: **<https://meok.ai/verify>**
