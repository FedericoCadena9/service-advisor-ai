# Are there public Mexican maintenance schedules for the demo fleet?

Retrieved 2026-07-31. Question asked of the manufacturers' own sites: for each of the ten
canonical vehicles, is there a public Mexican document that binds model, year, engine and
drivetrain to a maintenance interval, with a citable page?

## Answer: no, for all ten

Not one configuration has a public Mexican schedule at that resolution. Every rule in
`knowledge.py` therefore cites the manufacturer's United States manual and is labeled
`fallback_market: United States`. `review_state: reviewed` means the cited page was opened
and read — not that the foreign document is equivalent to a Mexican vehicle.

What does exist in Mexico is coarser and cannot substitute:

- Honda México publishes 10,000 km / 12 months normal and 5,000 km / 6 months severe for
  CR-V 2017–2026, but names no engine and no AWD.
- Ford México publishes a generic 15,000 km / 12 months programme for 2020 and later, with
  no split by engine, drivetrain or severe use.
- Toyota México's model pages did not expose a maintenance guide for these model years;
  historical public paths returned 403.

## What the manuals actually publish

The three brands do not describe service the same way, and a single interval in kilometres
can only express one of them.

| Brand | Shape | Detail |
| --- | --- | --- |
| Toyota | a distance | 10,000 mi / 16,093 km for Corolla and RAV4; 7,500 mi / 12,070 km for Tacoma |
| Ford | a range plus a monitor | normal 12,000–16,000 km, severe 8,000–12,000, extreme 5,000–8,000; the dashboard allows ≤800 km after the alert |
| Honda | no distance | the Maintenance Minder computes the service from condition; only sub-items carry distances (C2 at 24,000 km, C3 CVT at 40,000 km) |

This is why `MaintenanceRule` carries a `FixedInterval`, a `RangeInterval` or a
`ConditionInterval` rather than an integer. A condition-based rule answers that the odometer
does not decide, which is what the manual says.

## Known limitations

**The fleet is not plausibly Mexican.** Several canonical vehicles do not match the Mexican
line-up as specified: the Explorer XLT 2.3 sold in Mexico was RWD, the Ranger XLT 4x4 was
diesel, the Escape 2022 published was a hybrid, and RAV4 XLE AWD and Tacoma SR5 were not
Mexican trims. The vehicles were invented before the sources were researched.

**Engine displacement is not an identifier.** The 2021 F-150 "3.5L" may be an EcoBoost or a
PowerBoost hybrid, and the hybrid can exceed the standard oil-life maximum. A VIN or engine
code is required before that rule is applied to a real vehicle. The system already keys
retrieval on engine and drivetrain; this shows even that is not always enough.

**Severe use is not modelled.** Every manual distinguishes normal from severe operation, and
the check-in already captures a severe-use profile, but the rules do not yet consume it.

## Sources

Honda: [Civic 2019](https://owners.honda.com/utility/download?path=%2Fstatic%2Fpdfs%2F2019%2FCivic+Sedan%2F2019_Civic_4D_Maintenance_Minder.pdf),
[CR-V 2021](https://owners.honda.com/utility/download?path=%2Fstatic%2Fpdfs%2F2021%2FCR-V%2F2021_CR-V_Maintenance_Minder_System.PDF),
[Accord 2020](https://owners.honda.com/utility/download?path=%2Fstatic%2Fpdfs%2F2020%2FAccord+Sedan%2F2020_Accord_4D_Maintenance_Minder.pdf),
[Honda México](https://www.honda.mx/web/pdf/maintenance/MenuServicioHonda.pdf)

Toyota: [Corolla 2022](https://assets.sia.toyota.com/publications/en/omms-s/T-MMS-22Corolla/pdf/T-MMS-22Corolla.pdf),
[RAV4 2021](https://assets.sia.toyota.com/publications/en/omms-s/T-MMS-21RAV4/pdf/T-MMS-21RAV4.pdf),
[Tacoma 2020](https://assets.sia.toyota.com/publications/en/omms-s/T-MMS-2086/pdf/T-MMS-2086.pdf)

Ford: [F-150 2021](https://www.fordservicecontent.com/Ford_Content/Catalog/owner_information/2021-Ford-F-150-Owners-Manual-version-2_om_EN-US_10_2021.pdf),
[Escape 2022](https://www.fordservicecontent.com/Ford_Content/Catalog/owner_information/2022-Ford-Escape-Owners-Manual-version-1_om_EN-USA_09.2-2021.pdf),
[Explorer 2020](https://www.fordservicecontent.com/Ford_Content/Catalog/owner_information/2020-Ford-Explorer-Gas-Hev-Owners-Manual-version-3_om_EN-US_03_2020.pdf),
[Ranger 2021](https://www.fordservicecontent.com/Ford_Content/Catalog/owner_information/2021-Ford-Ranger-Owners-Manual-version-1_om_EN-US_10_2020.pdf),
[Ford México programme](https://www.ford.mx/propietarios/programa-mantenimiento/2020-posteriores.html)

Manual text is not reproduced here: these documents are copyrighted. What is stored is
provenance — URL, page, section, retrieval date — and the figures needed to cite them.
