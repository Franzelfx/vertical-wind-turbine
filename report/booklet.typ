// The booklet for friends: `uv run vawt pdf`, which writes build/report/data.json first.
// Prose lives here; every figure comes from data.json (ADR-009). Layout lengths use pt, cm and em,
// never mm, so tests/test_report.py can catch a figure typed by hand.

#let d = json("/build/report/data.json")

#let ink = rgb("#20272E")
#let muted = rgb("#5B6670")
#let hairline = rgb("#D5DBE0")
#let accent = rgb("#1F5A96")
#let tint = rgb("#EEF2F6")
#let warm = rgb("#FBF3E4")
#let warm-ink = rgb("#8A5A00")
#let night = rgb("#141D25")
#let title = "A small wind turbine for the garden"

#set document(
  title: title,
  description: "Design study of a 3D-printed vertical-axis wind turbine that charges a battery. Nothing has been built yet.",
)
#set text(font: "Avenir Next", size: 10.5pt, fill: ink, lang: "en", region: "GB")
#set par(leading: 0.62em, spacing: 0.95em)
#set list(indent: 0.2em, body-indent: 0.6em, spacing: 0.6em)
#set enum(indent: 0.2em, body-indent: 0.6em, spacing: 0.7em)
#set page(
  paper: "a4",
  margin: (x: 2cm, top: 1.8cm, bottom: 2cm),
  footer: context {
    set text(size: 7.5pt, fill: muted)
    grid(
      columns: (1fr, auto),
      [#title · design study, nothing built yet · private copy for friends],
      counter(page).display(),
    )
  },
)

#show heading.where(level: 1): it => {
  pagebreak(weak: true)
  block(above: 0pt, below: 0.9em, text(size: 21pt, weight: 600, it.body))
}
#show heading.where(level: 2): it => block(
  above: 1.25em,
  below: 0.55em,
  text(size: 11.5pt, weight: 600, it.body),
)

#let lead(body) = block(below: 1.1em, {
  set par(leading: 0.65em)
  text(size: 12.5pt, body)
})

#let tech(body) = block(
  fill: tint,
  inset: (x: 11pt, y: 10pt),
  radius: 3pt,
  width: 100%,
  above: 1.1em,
  {
    text(size: 7.5pt, weight: 600, fill: accent, tracking: 0.05em)[FOR THE TECHNICALLY MINDED]
    v(-0.25em)
    set text(size: 9pt)
    set par(leading: 0.58em, spacing: 0.75em)
    body
  },
)

#let warning(body) = block(
  fill: warm,
  inset: (x: 11pt, y: 10pt),
  radius: 3pt,
  width: 100%,
  above: 1em,
  body,
)

#let stat(value, label) = stack(
  dir: ttb,
  spacing: 7pt,
  text(size: 21pt, weight: 600, value),
  text(size: 9pt, fill: muted, label),
)

#let picture(name, alt, height: auto, width: 100%) = block(
  clip: true,
  radius: 3pt,
  below: 0.35em,
  width: width,
  height: height,
  image("/build/report/images/" + name + ".jpg", width: 100%, height: if height == auto { auto } else { 100% }, fit: "cover", alt: alt),
)
#let caption(body) = block(above: 0.35em, below: 0.9em, text(size: 8pt, fill: muted, body))

#let data-table(columns, header, rows, align: left, size: 8pt) = {
  set text(size: size)
  set par(leading: 0.5em)
  table(
    columns: columns,
    align: align,
    stroke: (x, y) => (bottom: 0.5pt + hairline),
    inset: (x: 4pt, y: 3.6pt),
    table.header(..header.map(h => text(weight: 600, fill: muted, h))),
    ..rows.flatten(),
  )
}

#let arrow = box(width: 100%, height: 1.1em, {
  place(horizon + left, line(length: 80%, stroke: 1pt + muted))
  place(horizon + right, rotate(90deg, polygon.regular(size: 6pt, vertices: 3, fill: muted, stroke: none)))
})
#let flow-box(name, plain, tech-term) = block(
  fill: tint,
  radius: 3pt,
  inset: 7pt,
  width: 100%,
  height: 8.2em,
  {
    set align(top + left)
    text(size: 9pt, weight: 600, name)
    v(-0.45em)
    text(size: 7.8pt, plain)
    place(bottom + left, text(size: 6.8pt, fill: accent, tech-term))
  },
)

// ------------------------------------------------------------------------------------------------
// Cover
// ------------------------------------------------------------------------------------------------

#page(margin: 0pt, footer: none, background: image("/build/report/images/render-site.jpg", width: 100%, height: 100%, fit: "cover", alt: "Computer render of the turbine on its timber post in a garden."))[
  #place(top + left, dx: 1.5cm, dy: 1.7cm, block(width: 8.1cm, {
    {
      set par(leading: 0.42em)
      text(size: 33pt, weight: 600, fill: night, title)
    }
    v(0.2em)
    text(size: 12pt, fill: night)[A 3D-printed turbine on a timber post that charges a battery, designed entirely on a computer.]
    v(0.9em)
    box(fill: night, radius: 2pt, inset: (x: 6pt, y: 4pt), text(size: 8pt, weight: 600, fill: white, tracking: 0.05em)[DESIGN STUDY])
    v(0.15em)
    text(size: 9.5pt, fill: night)[Nothing has been built yet. Every picture is a computer render and every power figure an estimate.]
  }))
  #place(bottom + left, block(fill: night.transparentize(10%), width: 100%, inset: (x: 1.5cm, top: 16pt, bottom: 15pt), {
    set text(fill: white)
    let tile(value, label) = stack(
      dir: ttb,
      spacing: 6pt,
      text(size: 19pt, weight: 600, value),
      text(size: 8.5pt, fill: rgb("#C7D0D8"), label),
    )
    grid(
      columns: (1fr, 1fr, 1fr, 1fr),
      column-gutter: 12pt,
      align: top + left,
      tile(d.rotor_h, [tall rotor, on a #d.pier_height post]),
      tile(d.pack_wh, [battery, about #d.phones_in_pack phone charges]),
      tile(d.cut_in, [light wind in which charging starts]),
      tile(d.mean_w, [average output, about #d.kwh_year a year]),
    )
    v(0.5em)
    text(size: 7.5pt, fill: rgb("#C7D0D8"))[Private copy for friends, not for publication. Built #d.version.]
  }))
]

// ------------------------------------------------------------------------------------------------
= The short version

#lead[This is a design for a wind turbine you could build at home. A twisted rotor, 3D-printed and about as tall as a kitchen counter, turns on the side of a timber post in the garden. It drives a small motor used as a generator, and electronics in a weatherproof box store the energy in a battery.]

The honest headline is that *it makes very little electricity*. This is a project to enjoy, not a way to save money.

#v(0.3em)
#grid(
  columns: (1fr, 1fr, 1fr),
  column-gutter: 14pt,
  stat(d.mean_w, [average output at the assumed #d.mean_wind mean wind: less than a small night light]),
  stat(d.euro_year, [roughly the value of a year's output, about #d.kwh_year, at #d.euro_kwh per kWh]),
  stat([#d.solar_ratio times], [what a #d.solar_w solar panel would make in the same year, about #d.solar_kwh]),
)

== What friends usually ask

#let qa(question, answer) = block(breakable: false, below: 0.85em, {
  text(weight: 600, question)
  v(-0.45em)
  answer
})

#columns(2, gutter: 16pt)[
  #qa[Has it been built?][No. So far it exists as a 3D model, a circuit diagram and a set of calculations. The pictures are computer renders, and the garden in them is made up too.]
  #qa[Why does it stand upright?][A vertical rotor doesn't need to turn to face the wind. It is also forgiving in the gusty, changing wind of a garden, and it makes a good-looking object.]
  #qa[Could it charge my phone?][Yes, indirectly. A full battery holds about #d.phones_in_pack phone charges, and it takes about #d.days_fill of typical wind to fill.]
  #colbreak()
  #qa[Is it safe?][Only if it's treated with respect. The rotor spins fast above head height and must be locked by hand before a storm. Page #context counter(page).at(<safety>).first() has the rules.]
  #qa[Is it noisy?][Nobody knows yet. Noise hasn't been estimated, so that will have to wait for the first real rotor.]
  #qa[What would it cost?][There's no full figure yet. Only the circuit board's parts are priced, at about #d.board_usd, without making the board or the rest of the build.]
]

== How to read this booklet

Each section starts in plain words, and you don't need any technical background for those parts. The blue boxes are *for the technically minded*, and everyone else can skip them. The reference pages at the end hold the full tables, parts lists and circuit diagrams.

#v(0.2em)
#{
  show outline.entry: it => link(it.element.location(), it.indented(none, [#it.body() #box(width: 1fr, repeat(gap: 3pt)[.]) #it.page()]))
  set text(size: 9pt)
  outline(title: none, depth: 1)
}

// ------------------------------------------------------------------------------------------------
= How it works

#lead[Wind pushes the rotor round. The turning rotor drives a generator, and electronics turn its unsteady output into something a battery can safely take.]

#{
  let gap = 11pt
  grid(
    columns: (1fr, gap, 1fr, gap, 1fr, gap, 1fr, gap, 1fr),
    align: horizon,
    flow-box([Rotor], [Wind pushes the twisted blades round.], [#d.rotor_size]),
    arrow,
    flow-box([Generator], [A small motor, run in reverse, makes electricity.], [#d.generator]),
    arrow,
    flow-box([Guard], [Rectifies the output and cuts off dangerous voltage.], [Bridge, relay]),
    arrow,
    flow-box([Charger], [Adapts any input to what the battery needs.], [BQ25798]),
    arrow,
    flow-box([Battery], [Stores the energy for whatever you connect.], [#d.pack_cells Li-ion, #d.pack_wh]),
  )
}
#v(0.3em)
#align(center, text(size: 8.5pt, fill: muted)[A tiny computer, the ESP32-C3, steers the charger so the rotor runs at its best speed, and reports over Wi-Fi.])

#v(0.4em)
#v(0.5em)
#picture("render-turbine-top", "Render of the top of the rotor, where it hangs from the model's own bracket on the post.", height: 10.6cm)
#caption[The top of the rotor, held by the original model's own bracket.]

== Why the rotor is unusual

The rotor comes from a model called the "Ugrinsky Style wind Turbine" by GeoJolt. It was designed as a spinning wall decoration, so it has no way to take power out. The new work in this project is the drive that gets power out of it, along with everything after that.

#tech[A drag-type rotor at tip speed ratio #d.tsr, with an assumed peak Cp of #d.cp. A 2-D CFD study reports 0.17 for this profile, but 2-D CFD flatters, and wind-tunnel rotors of this size reach about what is assumed here. Bench test B3 replaces the assumption.]

// ------------------------------------------------------------------------------------------------
= Where everything sits

#picture("render-site-labelled", "Render of the whole system with labels: upper bracket, rotor, generator, cable, enclosure, pier and ground socket.", height: 19.8cm)

#v(0.4em)
#columns(2, gutter: 16pt)[
  The post stands #d.pier_height tall. The rotor sits at the top, with its underside #d.rotor_bottom above the ground, out of reach. The generator hangs directly below it under a rain cover.

  #colbreak()
  A cable runs down the post to the box at chest height, about #d.box_height up, on the opposite side from the rotor. You can reach it without a ladder, and you're not standing under the rotor while you work on it.
]

// ------------------------------------------------------------------------------------------------
= What it delivers

#lead[The rotor makes real power only in strong wind, and strong wind is rare. In these charts, power multiplied by hours gives the energy that actually arrives over a year.]

#image("/build/report/power.svg", width: 100%, alt: "Three charts sharing a wind-speed axis. Power rises slowly and reaches its best at near gale force. Hours a year are concentrated at low wind speeds. Energy a year comes mostly from moderate to fresh winds.")
#caption[Estimates from the sizing model, accurate to about #d.accuracy until measured. Names along the top are Beaufort wind forces. The numbers are in the reference tables.]

#grid(
  columns: (1fr, 1fr),
  column-gutter: 16pt,
  [
    At the assumed #d.mean_wind average, the turbine charges about #d.charging_share of the time, though mostly at a trickle. Half of the year's energy arrives above #d.half_energy_wind, which happens only #d.half_energy_share of the time. Wind above #d.wind_ten blows for only about #d.hours_above_10 a year.
  ],
  [
    #data-table(
      (1fr, 1fr, 1fr, 1fr),
      ([Mean wind (m/s)], [Average (W)], [kWh a year], [Days to fill battery]),
      d.yield_rows,
      align: right,
    )
  ],
)

The site matters more than anything else in the design: a windier spot makes several times as much, as the table shows. A real wind log from the actual site will replace the assumption.

#tech[Assumes ideal input-voltage tracking, inside every limit: the charger's #d.charger_min minimum, the relay's #d.relay_trip trip, and the generator's #d.gen_current and #d.gen_copper copper limits. Above about #d.wind_ten the generator limits output, so firmware must let the rotor run faster at lower torque. Rayleigh wind distribution, #d.efficiency charger efficiency.]

// ------------------------------------------------------------------------------------------------
= Rotor and drive

#lead[The rotor is held at both ends on the side of the post. New printed parts underneath take the turning force down into the generator.]

#grid(
  columns: (7.2cm, 1fr),
  column-gutter: 16pt,
  [
    #picture("render-turbine", "Render of the rotor from below, on the side of the post.", height: 10.08cm)
    #caption[The rotor from below: #d.rotor_size, about #d.rotor_mass.]
  ],
  [
    The original model spins freely on two fixed bolts. To make electricity, the lower bearing is replaced by a new flange bolted through the rotor's floor. A steel rod runs from the flange through a printed bracket and down to the generator, joined by a flexible printed coupling that forgives small misalignments.

    Everything outdoors is printed in ASA rather than the model's PLA, because PLA softens in the sun.

    The generator is a #d.gen_mass gimbal motor, of the kind used to steady cameras. The usual hobby choice would be a stepper motor, but its magnetic "notches" would stop this weak rotor from starting at all.

    The rotor tip passes just #d.tip_clearance from the post.
  ],
)

#grid(
  columns: (1fr, 1fr),
  column-gutter: 12pt,
  [
    #picture("render-drive", "Render of the printed bracket and generator cover under the rotor.", height: 5.25cm)
    #caption[Drive bracket with its rain cover.]
  ],
  [
    #picture("render-drive-open", "Render of the bracket with the cover removed, showing the coupling and generator.", height: 5.25cm)
    #caption[Cover off: coupling above, generator below.]
  ],
)

#tech[Side-mounted because a #d.rotor_h cantilever on top of the post would overload an M8 shaft many times over, while supported at both ends the M8 stub sees about #d.stub_stress at #d.survival. Two 608 bearings sit #d.bearing_spacing apart on the original model's #d.reach reach. The generator runs at #d.kv, and the rotor makes only #d.torque_8 at #d.wind_eight. Weak spots: a printed bracket on a long reach, three M4 bolts in a printed floor, and the motor's fixing pattern, which is unconfirmed until bench test B1.]

// ------------------------------------------------------------------------------------------------
= The electronics

#lead[A wind turbine's output is awkward. It can be far below the battery's voltage in light wind and far above it in strong wind. The electronics have to cope with both, and protect themselves even with no battery and no working software.]

#grid(
  columns: (1fr, 8.4cm),
  column-gutter: 16pt,
  [
    == Taking whatever the wind gives

    The generator's voltage rises with speed, from about #d.charger_min to about #d.peak_bus in normal running. The battery wants #d.pack_range. The charger chip can step voltage both up and down to bridge that gap.
  ],
  [
    #picture("render-enclosure-open", "Render of the open enclosure: green circuit board above, blue battery pack below in a steel pan.", height: 5.25cm)
    #caption[Inside the box: the circuit board above, the battery below.]
  ],
)

The rotor also has a best speed for each wind. A tiny computer keeps adjusting how hard the charger pulls, hunting for the point of most power. That software isn't written yet. Without it the charger still works, but makes little power.

== The guard that needs no battery

When the battery is full, the charger stops taking power. With nothing holding it back, the rotor speeds up and its voltage climbs, passing the charger's #d.charger_max limit at about #d.wind_charger_limit and reaching about #d.bus_survival in a storm. That would destroy the charger.

So a simple relay sits in front of it, powered by that same rising voltage. At about #d.relay_trip it clicks open and disconnects the charger by itself, with no battery and no software needed.

== The cold-weather rule

Charging lithium batteries below freezing damages them and can make them unsafe. A temperature sensor on the battery stops charging outside #d.temp_min to #d.temp_max in hardware, so there is no charging on frosty days. Standing idle, the system draws so little (#d.standby) that the battery would last about #d.standby_years, and the cells' own self-discharge matters more.

#tech[Charger: BQ25798 buck-boost, set for 3S. Its built-in MPPT samples open-circuit voltage for solar panels, which would collapse the rotor's speed, so the ESP32-C3 hill-climbs VINDPM from the charger's ADC instead. Input stage: a Schottky bridge and a normally closed relay, with the coil on the raw bus through series resistors. Parts on that side are rated #d.relay_parts, the resistors reach #d.relay_watts at #d.survival, and the coil path draws about #d.coil_mw at a #d.bus_ref bus. Once picked up, the relay holds to a very low voltage, so the MCU pulses it to release; if that fails, it stays open, which is safe. The board is #d.board_size, placed but not routed.]

// ------------------------------------------------------------------------------------------------
= The weatherproof box

#lead[A battery and electronics have to live outdoors for years on a post, through rain, sun and condensation. The box is 3D-printed, about the size of a large paperback, with nothing that opens upwards for rain to find.]

#grid(
  columns: (1fr, 1fr),
  column-gutter: 12pt,
  [
    #picture("render-enclosure", "Render of the closed grey enclosure on the post, under its rain hood.", height: 5.25cm)
    #caption[Closed, with its separate rain hood.]
  ],
  [
    #picture("render-enclosure-exploded", "Exploded render of the enclosure showing tub, board, battery, lid and screws.", height: 5.25cm)
    #caption[Exploded: tub, board, battery and lid.]
  ],
)

#grid(
  columns: (1fr, 5.7cm),
  column-gutter: 16pt,
  {
    list(
      [*Printed in pale grey ASA*, which resists sunlight and reflects heat.],
      [*A rubber cord in the rim* seals the lid, held by six screws outside the seal.],
      [*Everything enters from below*: two cable glands, a brake switch and a vent. The vent stops pressure swings from sucking in damp air past the seal.],
      [*A separate hood* shades the lid and sheds rain, with an air gap so the sun doesn't reach it.],
      [*Spacers keep it off the wood*, so the post can dry behind it.],
      [*It should face north*, away from the sun.],
    )
  },
  [
    #picture("render-enclosure-below", "Render of the enclosure from below, showing the glands, vent and switch.", height: 3.56cm)
    #caption[From below: glands, vent and brake switch.]
  ],
)

#warning[*A printed box will not contain a battery fire.* A real battery management system and a steel pan reduce the risk, but they don't remove it. Mount the box away from buildings and anything that burns easily.]

#tech[#d.box_size overall. #d.gasket EPDM cord at #d.squeeze squeeze, #d.hood_gap hood gap, #d.standoff standoffs. Four M6 coach screws land on the post, all outside the sealed volume. Print with at least 4 perimeters, then prove it with seal test B6: a hose, paper inside, and a winter night for condensation.]

// ------------------------------------------------------------------------------------------------
= Safety and limits <safety>

#lead[A small turbine is still a fast-spinning object on a pole, with a lithium battery attached. None of this has been tested or certified, so these rules come first.]

#warning[
  *It is not storm-proof unattended.* If a storm comes with nobody home to fit the pin, the rotor runs free. It reaches its assumed speed limit at about #d.free_limit_wind, and it could then throw parts from height.
]

== The rules

#enum(
  [*Lock the rotor before any storm.* A #d.pin steel parking pin locks it to the bracket. The strength calculations for storm wind (#d.survival) all assume the pin is fitted.],
  [*Fit the pin before touching the turbine*, every time. The tips move fast, even when it looks gentle.],
  [*Keep the fall zone clear:* about the post's own height, #d.fall_zone, all the way around. No paths, seats or play areas.],
  [*Spin-test first.* Nothing goes up the post until the rotor has been spun up and balanced on the ground, outdoors and behind cover.],
  [*Keep the battery away from buildings*, and use a bought pack with a real battery management system.],
  [*Don't count on the brake switch.* It only slows the rotor in light wind, long enough to fit the pin. It cannot stop it in a storm.],
)

== What could go wrong, and what's in place

#data-table(
  (1.15fr, 1.5fr, 1.2fr),
  ([Risk], [What the design does], [What it still relies on]),
  (
    ([Rotor overspeeds in a storm], [Parking pin], [A person fitting it in time]),
    ([Parts thrown from height], [Rotor underside #d.rotor_bottom up, spin test before mounting], [The fall zone staying clear]),
    ([Charger destroyed by high voltage], [Relay opens by itself at #d.relay_trip], [The relay behaving as specified; not yet tested]),
    ([Battery charged below freezing], [Temperature sensor cuts charging in hardware], [The sensor being fitted on the pack]),
    ([Battery fire], [Bought pack with BMS, fuses, steel pan], [Mounting away from anything that burns]),
    ([Post shakes at a certain wind], [Small calculated swing, #d.swing], [Balancing the rotor; a real test on the post]),
  ),
  size: 8.5pt,
)

#tech[At #d.survival with the pin fitted, the pier's utilisation is #d.utilisation and it deflects #d.deflection at rotor height. Its first mode is #d.mode_hz, or #d.mode_rpm, which the rotor reaches at about #d.mode_wind, right in the everyday range. Hence the balancing. The brake holds #d.brake_rpm at #d.brake_wind with #d.brake_w in the generator, and reaches the generator's limit at #d.brake_limit_wind. An automatic centrifugal brake would make it safe unattended, but that's a project of its own.]

// ------------------------------------------------------------------------------------------------
= Where it stands, and what's next

#lead[The digital design is done and passes its automated checks. Nothing has been printed, soldered, or measured, so every claim in this booklet is still on paper.]

#grid(
  columns: (1fr, 7.6cm),
  column-gutter: 18pt,
  {
    heading(level: 2)[Real tests, cheapest first]
    set text(size: 9.5pt)
    let test(name, body) = block(below: 0.6em, [*#name.* #body])
    test([B1 Generator], [Measure the motor with a meter and a drill. Everything rests on it, and it costs little.])
    test([B2 Electronics], [Check charger efficiency, and prove the relay trips.])
    test([B3 Rotor curve], [Measure real torque and speed, in a car on a calm day or by a large fan. This changes every power figure most.])
    test([B4 Spin and balance], [Spin the rotor up in steps behind cover, watching for cracks. Nothing goes up the post before this passes.])
    test([B5 Site], [Log the real wind for a month, and pluck the post to find how it shakes.])
    test([B6 Seal], [Hose the box for half an hour with paper inside, then leave it out on a winter night.])
  },
  {
    heading(level: 2)[Progress]
    set text(size: 8.5pt)
    let bar(done, total) = {
      let share = if total == 0 { 0% } else { done / total * 100% }
      box(width: 100%, height: 0.5em, fill: tint, radius: 1pt, clip: true, box(width: share, height: 100%, fill: accent))
    }
    table(
      columns: (1fr, 2cm, auto),
      align: (left + horizon, horizon, right + horizon),
      stroke: none,
      inset: (x: 2pt, y: 2.4pt),
      ..d.progress.map(p => (p.title, bar(p.done, p.total), [#p.done/#p.total])).flatten(),
    )
    v(-0.3em)
    text(size: 8pt, fill: muted)[Items ticked in the project's plans. M: mechanical, E: electronics, B: bench tests.]
  },
)

== What's still unknown

There are #d.assumptions_total assumed numbers behind this design, listed in the reference pages. The biggest are how well the rotor actually catches wind, how much wind the site gets, and how fast the printed rotor can safely spin. Treat every power figure as #d.accuracy until those are measured. A failed test would be a useful result, and could change the design.

== Who decided what

An AI assistant, Claude, did most of the design work with the project's owner. The choices that shape safety and the build, such as mounting the rotor on the side and parking it by hand, were the owner's. The electronics and the box were proposed by Claude and *haven't yet had a human review*, and the circuit has only passed automated checks.

#data-table(
  (auto, 1fr, auto),
  ([Record], [Decision], [Status]),
  d.decision_rows,
)

== Credits

The rotor and upper bracket are the "Ugrinsky Style wind Turbine" by GeoJolt, from MakerWorld, under its Standard Digital File License: personal use, with no redistribution of the files. The files aren't part of this project or this booklet, and the licence hasn't yet been checked for sharing renders, which is why this is a private copy. Made with FreeCAD, KiCad, Blender and Typst.

// ------------------------------------------------------------------------------------------------
= Reference: figures

Everything here comes straight from the project's model. Evidence: *M* measured from a real file, *S* from a named source, *E* an estimate. Everything holds on paper only.

== Requirements: #d.requirements_total limits, all checked automatically

#data-table(
  (auto, 1fr, auto, auto, auto, auto),
  ([ID], [Requirement], [Limit], [Now], [Evid.], [Holds]),
  d.requirement_rows,
  size: 7.6pt,
)

#pagebreak()

== Best operating point at each wind

#data-table(
  (1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
  ([Wind (m/s)], [Rotor (rpm)], [Torque (N m)], [Current (A)], [Bus (V)], [Copper loss (W)], [Into battery (W)]),
  d.power_rows,
  align: right,
  size: 7.6pt,
)
#caption[Zero means the relay has opened and the rotor runs free. The best point is #d.peak_w at #d.peak_wind.]

#grid(
  columns: (5.8cm, 1fr),
  column-gutter: 16pt,
  [
    == Structure at #d.survival, pin fitted

    #data-table((1fr, auto), ([Item], [Value]), d.structure_rows, size: 7.6pt)
  ],
  [
    == Numbers nobody has measured

    #data-table((auto, 1fr), ([Value], [Basis, and the test that replaces it]), d.assumption_rows, size: 7.6pt)
  ],
)

// ------------------------------------------------------------------------------------------------
= Reference: parts

The rotor and its upper bracket are printed from the licensed model and aren't listed here. Battery size is still to be checked against the tray. No full-system price exists yet.

#grid(
  columns: (1fr, 1fr),
  column-gutter: 14pt,
  [
    == Mechanical

    #data-table((1fr, auto, 0.8fr), ([Item], [Qty], [Use]), d.mechanical_rows, size: 7.6pt)
  ],
  [
    == Electrical

    #data-table((1fr, auto, 0.8fr), ([Item], [Qty], [Use]), d.electrical_rows, size: 7.6pt)
  ],
)

== Printed parts

#data-table(
  (auto, auto, auto, 1fr, auto, auto),
  ([Part], [Qty], [Material], [How it lies on the bed], [Size (mm)], [Supports]),
  d.print_rows,
  size: 7.6pt,
)
#caption[All fit a #d.bed print bed. Print enclosure parts with at least 4 perimeters.]

#pagebreak()

== Circuit board parts

Stock and prices as of #d.bom_date, single-unit tier: about #d.board_usd in all, without fabrication and assembly. Some parts aren't on this supplier's list and are fitted by hand.

#data-table(
  (1.5fr, auto, 1fr, auto, 1.5fr, auto),
  ([Parts], [Qty], [Value], [LCSC], [Manufacturer's part], [USD]),
  d.bom_rows,
  size: 7pt,
)

// ------------------------------------------------------------------------------------------------
// Circuit diagram. Sheet 1 of the PDF is only KiCad's index of the other three.
// ------------------------------------------------------------------------------------------------

#show heading.where(level: 1): it => block(below: 0.6em, text(size: 21pt, weight: 600, it.body))
#for (sheet, name, wide) in ((2, "Input stage", false), (3, "Charger", true), (4, "Controller", false)) {
  page(flipped: wide, margin: (x: 1cm, top: 1.2cm, bottom: 1.6cm))[
    #if sheet == 2 [= Reference: circuit diagram]
    #image("/docs/images/charge-board-schematic.pdf", page: sheet, width: 100%, height: 1fr, fit: "contain", alt: "Circuit diagram of the charge board: " + name + ".")
    #align(center, text(size: 8pt, fill: muted)[#name. Passes KiCad's electrical rules check; not yet reviewed by a person.])
  ]
}
