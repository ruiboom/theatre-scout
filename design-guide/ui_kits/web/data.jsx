// Theatre Scout — fixture data for the click-thru
const SHOWS = [
  { title: "Hamlet", tag: "PLAY · TRAGEDY", venue: "Almeida Theatre", dates: "14 May – 28 Jun", area: "Islington", price: "£25–95", running: "3h 10m incl. interval", director: "Rebecca Frecknall", cast: "Andrew Scott, Jessie Buckley, Adrian Lester", booking: "Now booking through 28 June 2026.", synopsis: "A son returns from university to find his father dead and his uncle on the throne. He suspects foul play; he may be losing his mind." },
  { title: "The Cherry Orchard", tag: "PLAY · REVIVAL", venue: "Donmar Warehouse", dates: "02 Jun – 09 Aug", area: "Covent Garden", price: "£10–60", running: "2h 30m incl. interval", director: "Benedict Andrews", cast: "Nicole Kidman, Adeel Akhtar, Tara Fitzgerald", booking: "Booking opens to members 14 May.", synopsis: "A family returns to its ancestral estate to find the bank threatening to repossess. Nobody can quite bring themselves to leave." },
  { title: "A Midsummer Night's Dream", tag: "PLAY · SHAKESPEARE", venue: "Bridge Theatre", dates: "21 May – 12 Sep", area: "London Bridge", price: "£15–80", running: "2h 50m incl. interval", director: "Nicholas Hytner", cast: "Ensemble company", booking: "Now booking.", synopsis: "Lovers, fairies, and a troupe of amateur actors collide in a forest outside Athens. In this production, the audience stands in the forest." },
  { title: "Faith Healer", tag: "PLAY · MONOLOGUE", venue: "Lyttelton, NT", dates: "08 Jun – 30 Aug", area: "Southbank", price: "£20–95", running: "2h 20m incl. interval", director: "Rachel O'Riordan", cast: "Cillian Murphy", booking: "Now booking.", synopsis: "Three monologues, three unreliable narrators, one travelling faith healer. Brian Friel's 1979 play." },
  { title: "Operation Mincemeat", tag: "MUSICAL · COMEDY", venue: "Fortune Theatre", dates: "Open run", area: "Covent Garden", price: "£25–125", running: "2h 35m incl. interval", director: "Robert Hastie", cast: "SpitLip", booking: "Now booking through 04 January 2027.", synopsis: "Five actors. A corpse with fake papers. A wartime deception that may have changed everything. Olivier-winning musical." },
  { title: "The Real Thing", tag: "PLAY · REVIVAL", venue: "Old Vic", dates: "12 Jul – 27 Sep", area: "Waterloo", price: "£15–125", running: "2h 30m incl. interval", director: "Max Webster", cast: "James Norton, Bel Powley", booking: "Booking opens 30 May.", synopsis: "Tom Stoppard's 1982 comedy about playwrights, marriage, and the slippery question of what's authentic and what's a performance." },
];

const RAILS = [
  { idx: 1, title: "Opening this week", count: 14, picks: [0, 1, 4, 5] },
  { idx: 2, title: "Closing soon", count: 9,  picks: [3, 2, 5, 0] },
  { idx: 3, title: "Editor's index", count: 24, picks: [1, 3, 5, 4] },
  { idx: 4, title: "Under £20", count: 47, picks: [2, 0, 4, 1] },
];

window.SHOWS = SHOWS;
window.RAILS = RAILS;
