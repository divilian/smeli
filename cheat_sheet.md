# DOI cheat sheet

The central idea is simple:

> A DOI is a persistent identifier for a thing.  
> DOI registration agencies maintain DOI records and metadata.  
> `doi.org` resolves DOIs.  
> APIs such as Crossref, DataCite, and OpenAlex expose metadata about scholarly things, but they do not all play the same role.

---

## 1. The map of the territory

There are four different layers that are easy to blur together.

| Layer | Main question | Examples |
|---|---|---|
| Identifier layer | “What stable name identifies this thing?” | DOI, ORCID iD, ROR ID, ISSN, ISBN, PMID, arXiv ID |
| Registration / stewardship layer | “Who is responsible for creating and maintaining that identifier record?” | DOI Foundation, Crossref, DataCite, ORCID, ROR |
| Resolution layer | “When someone uses the identifier, where does it go?” | `doi.org`, Handle System, DOI target URL, landing page |
| Metadata / discovery layer | “What information can I retrieve about the thing?” | Crossref REST API, DataCite REST API, OpenAlex API, content negotiation |

For DOI lookup tooling, the most important distinction is:

- **A DOI resolver** tells you where a DOI points.
- **A DOI registration agency API** tells you what metadata was deposited with that agency.
- **An aggregator API** tells you what a large index has inferred, merged, or collected from multiple sources.

Those can agree, but they are not the same source of truth.

---

## 2. The shortest possible explanation

A **persistent identifier** (PID) is a durable identifier intended to keep referring to the same object over time, even if the object's web location changes.

A **DOI** is a PID for an object: an article, book chapter, dataset, software release, report, grant, physical object, standard, or other citable/trackable thing. It has a prefix and suffix, as in:

```text
10.1000/182
```

A DOI is made actionable by writing it as a URL:

```text
https://doi.org/10.1000/182
```

`doi.org` is the common DOI resolver. It looks up the DOI record and usually redirects you to a landing page maintained by the publisher, repository, or other responsible party.

A **registration agency** is an organization authorized within the DOI system to register DOI names and maintain metadata services for a community. **Crossref** and **DataCite** are two important registration agencies.

**Crossref** is the major DOI registration agency for scholarly publishing metadata: journal articles, books, chapters, conference papers, reports, grants, and related research objects.

**DataCite** is the major DOI registration agency for research data and many other research outputs/resources: datasets, software, samples, instruments, preprints, dissertations, grants, and more.

**ORCID** is a persistent identifier for people, not works. A paper can have a DOI; a researcher can have an ORCID iD.

**OpenAlex** is not a DOI registration agency. It is a large open scholarly metadata index/graph. It aggregates, deduplicates, disambiguates, and connects works, authors, institutions, sources, publishers, funders, and topics. It is often very useful, but it is not the original DOI registrar.

---

## 3. Identifier terms

**→** A **persistent identifier (PID)** is an identifier intended to remain stable over time. The point is not merely uniqueness but durable reference.

Examples:

- DOI: identifies objects/works/resources.
- ORCID iD: identifies researchers and contributors.
- ROR ID: identifies research organizations.
- ISSN: identifies serial publications such as journals.
- ISBN: identifies book editions.
- PMID: identifies PubMed records.
- arXiv ID: identifies arXiv submissions.
- RAiD: identifies research activities/projects.
- SWHID: identifies software artifacts in Software Heritage.

The word “persistent” does not mean “magic.” Persistence depends on institutions, policies, metadata maintenance, and responsible stewardship.

**→** An **identifier** says what something is. A **locator** says where to get it.

A URL is usually a locator. A DOI is intended to be an identifier that can be resolved to one or more current locators.

Example:

```text
DOI:         10.1145/337292.337296
DOI URL:     https://doi.org/10.1145/337292.337296
Target URL:  the publisher's current landing page for that work
```

If the publisher reorganizes its website, the target URL may change. The DOI should not.

**→** A **DOI** is a Digital Object Identifier. It identifies an object, which may be digital, physical, or abstract.

A DOI has two main parts:

```text
10.xxxx/yyyy
```

- The **prefix** begins with `10.` and is assigned through the DOI system.
- The **suffix** is chosen by the registrant within that prefix.
- The combination of prefix and suffix is the DOI name.

A DOI is usually displayed as a URL:

```text
https://doi.org/10.xxxx/yyyy
```

That is the preferred human-friendly form because it is directly clickable.

### DOI name, DOI URL, and DOI resolver

These are related but not identical.

| Term | Example | Meaning |
|---|---|---|
| DOI name | `10.1000/182` | The identifier itself |
| DOI URL | `https://doi.org/10.1000/182` | A web-actionable representation of the DOI |
| DOI resolver | `doi.org` | The service that resolves the DOI |
| Target URL | Publisher/repository landing page | Where the resolver redirects |

A DOI is not the same thing as a PDF URL. A DOI often resolves to a landing page, not directly to the PDF.

**→** The **prefix** is the part before the slash:

```text
10.1145
```

A prefix is allocated by a DOI registration agency. In practice, a prefix is associated with a registrant/member/repository account, not necessarily with a single journal or a single publisher brand.

**→** The **suffix** is the part after the slash:

```text
337292.337296
```

The registrant chooses the suffix, subject to the rules and practices of its registration agency.

Do not rely on suffixes being meaningful. Some look meaningful, but they are identifiers, not metadata.

### Case normalization

DOI lookup code should tolerate common DOI presentation differences:

```text
https://doi.org/10.1234/ABC
http://dx.doi.org/10.1234/ABC
doi:10.1234/ABC
10.1234/ABC
```

For lookup, it is common to strip the URL/proxy prefix, trim whitespace, and normalize the DOI string. DOI comparison is generally case-insensitive for ordinary ASCII characters, and Crossref/DataCite both advise that suffix case should not matter. For display, the modern best practice is usually lowercase DOI URLs.

**→** An **ORCID** (**Open Researcher and Contributor ID**) is a persistent identifier for an individual researcher/contributor.

Example form:

```text
https://orcid.org/0000-0002-1825-0097
```

Important distinction:

- DOI: identifies a work/resource/object.
- ORCID iD: identifies a person.
- ROR ID: identifies an organization.

A metadata record for a DOI may include ORCID iDs for authors/creators, but the ORCID iD is not part of the DOI.

**→** A **ROR** is a **Research Organization Registry**. A **ROR ID** identifies an organization, such as a university, lab, funder, archive, or research institute.

ROR IDs are often used in affiliation metadata, funder metadata, and organization disambiguation.

### ISSN and ISBN

**→** An **ISSN** identifies a serial publication, such as a journal or magazine.

**→** An **ISBN** identifies a book edition or book-like product.

They are not DOI substitutes. A journal may have an ISSN, an article in that journal may have a DOI, and a journal publisher may have Crossref membership.

### PMID, PMCID, and arXiv ID

These are domain-specific identifiers.

- **PMID** identifies a PubMed record.
- **PMCID** identifies a full-text article in PubMed Central.
- **arXiv ID** identifies an arXiv preprint/submission.

A single scholarly work may have several identifiers: DOI, PMID, PMCID, arXiv ID, OpenAlex ID, Semantic Scholar ID, and so on. They may point to different records about the same work.

---

## 4. Organizations and roles

**→** The **DOI Foundation** governs the DOI system. It is the registration authority for the ISO DOI standard and coordinates the shared infrastructure used by DOI registration agencies.

It is not the publisher of every DOI-bearing object. It is the standards/governance layer.

Think:

```text
DOI Foundation
    ↓ authorizes / coordinates
Registration Agencies
    ↓ serve communities and registrants
Registrants / publishers / repositories
    ↓ register DOI names and deposit metadata
DOIs
```

**→** A **registration agency** (RA) is an organization within the DOI system that provides DOI services to a particular community.

RAs typically:

- allocate DOI prefixes,
- register DOI names,
- define or maintain metadata schemas/profiles,
- collect metadata,
- provide update mechanisms,
- provide discovery or API services,
- enforce community-specific rules and obligations.

Crossref and DataCite are both DOI registration agencies. They overlap in some content types, but they have different histories, communities, schemas, APIs, and expectations.

**→** A **registrant** is the organization or person that registers a DOI with a registration agency.

In scholarly contexts, a registrant might be:

- a journal publisher,
- a university press,
- a repository,
- a data archive,
- a research institution,
- a government agency,
- a funder,
- a museum or collection-holding organization,
- a conference proceedings publisher.

The registrant is responsible for maintaining the DOI’s target URL and associated metadata, either directly or through arrangements with the registration agency or platform provider.

**→** A **member** is an organization that has joined a service such as Crossref or DataCite. In many practical contexts, “member” is the organization that deposits DOI metadata.

Do not assume that:

```text
member == publisher == journal == prefix owner
```

Those often line up, but not always.

**→** The word **publisher** is overloaded.

It can mean:

1. The organization that publishes a scholarly work.
2. The entity named in a citation as the publisher.
3. A metadata field in Crossref, DataCite, OpenAlex, or another schema.
4. The organization responsible for depositing or maintaining metadata.
5. A platform, imprint, repository, university, society, or commercial press.

In DataCite-style metadata, the publisher field can be broad: it may be the entity that holds, archives, publishes, distributes, releases, issues, or produces the resource. For datasets, software, and archival objects, this may be a repository or institution rather than a conventional publishing house.

**→** A **repository** is a place where research outputs are deposited, managed, and made available. Examples include institutional repositories, data repositories, Zenodo, Figshare, Dryad, OSF, and domain-specific archives.

A repository may register DOIs through DataCite or another RA. Some repositories act much like publishers for citation purposes.

**→** A **platform provider** hosts or manages publishing/repository infrastructure. Examples might include journal platforms, repository platforms, or DOI-management services.

A platform may help deposit metadata, but it is not necessarily the registrant, publisher, or registration agency.

---

## 5. Crossref, DataCite, and OpenAlex

### Crossref

**Crossref** is a DOI registration agency and metadata infrastructure organization for scholarly communications.

Crossref members register content and deposit metadata. Crossref’s metadata commonly includes:

- DOI,
- title,
- authors,
- publication date,
- journal/book/conference information,
- publisher,
- ISSN/ISBN,
- references,
- funder information,
- license information,
- ORCID iDs,
- abstracts when available,
- update/retraction/correction metadata when deposited.

Crossref has a public REST API. A common lookup pattern is:

```text
https://api.crossref.org/works/{doi}
```

Crossref is usually the first place to try for journal articles and many books/chapters/conference papers. But Crossref does not know every DOI.

### DataCite

**DataCite** is a DOI registration agency focused on research outputs and resources, including much more than traditional articles.

DataCite is especially important for:

- datasets,
- software,
- preprints,
- dissertations,
- samples,
- instruments,
- images,
- physical objects,
- grants,
- project outputs,
- repository-hosted research artifacts.

DataCite maintains the DataCite Metadata Schema and provides a REST API. A common lookup pattern is:

```text
https://api.datacite.org/dois/{doi}
```

DataCite metadata is often more suitable than Crossref metadata for non-article research objects.

### OpenAlex

**OpenAlex** is an open catalog/index of the global research system. It models scholarly entities and their connections.

OpenAlex entities include:

- works,
- authors,
- sources,
- institutions,
- topics,
- publishers,
- funders.

OpenAlex is extremely useful for discovery, enrichment, disambiguation, and graph-style questions. For example:

```text
https://api.openalex.org/works/doi:{doi}
```

But OpenAlex is **not** a DOI registration agency. It is an aggregator/index. It may combine information from Crossref, DataCite, PubMed, institutional sources, repositories, web crawls, and other signals.

For a DOI CLI, OpenAlex is often a good fallback or enrichment source, but not always the most authoritative source for the DOI’s deposited metadata.

### Side-by-side comparison

| Service | What it is | Best for | Not best for |
|---|---|---|---|
| `doi.org` | DOI resolver/proxy | Going from DOI to landing page; content negotiation | Rich search across works |
| Crossref | DOI registration agency + metadata API | Journal articles, books, chapters, conference papers, references | Every DOI in existence |
| DataCite | DOI registration agency + metadata API | Datasets, software, repository objects, research resources | Assuming article-like metadata |
| OpenAlex | Aggregator/index/graph | Discovery, enrichment, author/institution/source graph, deduplication | Treating as original DOI registrar |
| ORCID | PID registry for people | Identifying researchers/contributors | Identifying works |
| ROR | PID registry for organizations | Identifying institutions/funders/affiliations | Identifying people or works |

---

## 6. DOI resolution and `doi.org`

### Resolution

**Resolution** is the act of taking an identifier and using it to get something useful back.

For a DOI, normal browser resolution looks like this:

```text
User opens https://doi.org/10.xxxx/yyyy
    ↓
doi.org looks up DOI record
    ↓
doi.org redirects to current target URL
    ↓
browser lands on publisher/repository landing page
```

The target URL can change while the DOI stays the same.

### `doi.org`

`doi.org` is the standard web proxy/resolver for DOI names. It makes DOIs usable as ordinary web links.

Old DOI links often use:

```text
http://dx.doi.org/10.xxxx/yyyy
```

Modern display should use:

```text
https://doi.org/10.xxxx/yyyy
```

### Landing page

A **landing page** is the human-facing page for a work/resource. It usually includes title, authors, citation information, abstract/description, links to PDF or data files, license information, and access options.

A DOI should resolve to a landing page, not necessarily directly to a file.

This is deliberate. A landing page can provide context, metadata, access conditions, version information, citations, related objects, and license terms.

### Target URL

The **target URL** is the URL currently stored behind the DOI. It is where the resolver sends the user.

For persistence to work, the registrant must update the target URL if the content moves.

### Multiple resolution

Some DOI records can support multiple possible destinations or representations. The DOI system can support richer resolution than simple “one DOI → one URL,” although the common browser experience is a redirect to a landing page.

---

## 7. Content negotiation

### Content negotiation

**Content negotiation** is an HTTP mechanism where the client asks for a preferred representation of a resource by sending an `Accept` header.

For DOI lookup, that means you can ask `doi.org` for metadata in a particular format instead of just following the browser redirect.

Example:

```bash
curl -LH "Accept: application/vnd.citationstyles.csl+json" \
  https://doi.org/10.1145/337292.337296
```

You might also request formats such as BibTeX:

```bash
curl -LH "Accept: application/x-bibtex" \
  https://doi.org/10.1145/337292.337296
```

The exact result depends on the DOI, the registration agency, and the supported representation.

### Content negotiation vs API

These are different tools.

| Method | What you send | What you get |
|---|---|---|
| Browser DOI resolution | DOI URL | Redirect to landing page |
| DOI content negotiation | DOI URL + `Accept` header | Citation/metadata representation |
| Crossref REST API | Crossref endpoint | Crossref metadata JSON |
| DataCite REST API | DataCite endpoint | DataCite metadata JSON |
| OpenAlex API | OpenAlex endpoint | Aggregated OpenAlex work record |

Content negotiation is convenient when you have a DOI and want a citation-ish format.

A registration agency API is often better when you want rich structured metadata, agency-specific fields, search, filters, facets, or diagnostics.

An aggregator API is useful when you want enriched, reconciled, or graph-oriented metadata.

---

## 8. Metadata terms

### Metadata

**Metadata** is data about a thing.

For a scholarly work, metadata may include:

- title,
- creators/authors,
- contributors,
- publication year,
- publication venue,
- volume/issue/pages,
- abstract,
- DOI,
- URL,
- publisher,
- license,
- references,
- funder,
- affiliations,
- ORCID iDs,
- ROR IDs,
- related identifiers,
- resource type,
- version,
- language,
- subjects/keywords.

Metadata quality varies. A DOI can exist with incomplete, stale, or incorrect metadata.

### Metadata record

A **metadata record** is the structured record associated with an identifier or indexed object.

Examples:

- Crossref work record,
- DataCite DOI record,
- OpenAlex work record,
- ORCID record,
- ROR organization record.

A metadata record is not the thing itself. It is a description of the thing.

### Metadata schema

A **metadata schema** defines the fields, structure, and rules for metadata records.

Examples:

- Crossref metadata schema,
- DataCite Metadata Schema,
- CSL-JSON,
- BibTeX,
- RIS,
- Dublin Core,
- schema.org.

A DOI registration agency may define its own schema or profile to serve its community.

### Deposited metadata

**Deposited metadata** is metadata submitted to a registration agency by a member/registrant or trusted source.

For example, a publisher may deposit article metadata with Crossref. A repository may deposit dataset metadata with DataCite.

This matters because deposited metadata is usually closer to the responsible party, but it can still be incomplete or wrong.

### Enriched metadata

**Enriched metadata** has been improved, merged, inferred, disambiguated, or connected by another service.

OpenAlex records are often enriched: they may connect works to authors, institutions, concepts/topics, funders, sources, and citations using multiple data sources.

Enrichment is useful, but it can introduce mismatches or uncertainty.

### Canonical record

A **canonical record** is the record your system treats as authoritative for a particular purpose.

There is no universal canonical metadata source for all scholarly objects.

A practical DOI lookup tool might use different canonical sources depending on the DOI:

- Crossref record for Crossref-registered articles.
- DataCite record for DataCite-registered datasets/software.
- OpenAlex record for enrichment, search, or graph fields.
- `doi.org` resolution for target URL behavior.

### Work

A **work** is a scholarly output such as an article, dataset, book chapter, report, dissertation, preprint, or software release.

Crossref, DataCite, and OpenAlex all use work/resource-like concepts, but their models are not identical.

### Resource

**Resource** is a broad term common in DataCite-style contexts. It can refer to datasets, software, samples, images, text, physical objects, instruments, and other research outputs.

### Creator, author, contributor

These terms overlap but are not identical.

- **Author** is common for articles/books.
- **Creator** is common in DataCite and is broader; it means the main person or organization responsible for creating the resource.
- **Contributor** is a broader supporting role: editor, data curator, supervisor, funder, project member, contact person, rights holder, and so on.

A DOI metadata record may contain some, all, or none of these role distinctions.

### Source, venue, journal, container

A **source** or **venue** is where a work appears.

Examples:

- journal,
- conference proceedings,
- book,
- repository,
- preprint server.

OpenAlex uses “source” for venues such as journals, repositories, and conferences.

Crossref has fields for container titles such as journal title or book title.

### References and citations

A **reference** is an item listed by a work as something it cites.

A **citation** is a relationship: Work A cites Work B.

Metadata APIs may expose references, citation counts, or citation relationships, but coverage varies by source and by what publishers/repositories deposit.

### License metadata

**License metadata** describes reuse rights. It may point to a Creative Commons license, publisher license, data license, or custom terms.

Do not infer that a work is open access merely because it has a DOI. DOI resolution is free; the content may still be paywalled or restricted.

### Full text links

A DOI metadata record may include links to full text, PDFs, XML, or other files. These are not guaranteed.

Crossref and DataCite often know about landing pages and sometimes about full-text/resource links. OpenAlex and Unpaywall may be better for open-access location discovery.

### Related identifiers

**Related identifiers** are links from one identified object to another.

Examples:

- dataset `IsSupplementTo` article,
- preprint `IsPreprintOf` published article,
- software `IsSupplementTo` dataset,
- article `References` another DOI,
- work `IsVersionOf` another work.

Related identifiers are crucial for making scholarly infrastructure more graph-like instead of just a bag of records.

---

## 9. API terms

### API

An **API** is an interface for programs. In this context, it usually means an HTTP service that returns metadata in JSON or another machine-readable format.

### REST API

A **REST API** exposes resources through URLs and HTTP methods.

Examples:

```text
GET https://api.crossref.org/works/10.xxxx/yyyy
GET https://api.datacite.org/dois/10.xxxx/yyyy
GET https://api.openalex.org/works/doi:10.xxxx/yyyy
```

### Aggregator API

An **aggregator API** exposes data collected, merged, or indexed from multiple upstream sources.

OpenAlex is a good example. It is not merely returning one publisher’s deposited record; it is presenting a reconciled view of a large scholarly graph.

Aggregator APIs are useful for:

- finding works when exact DOI lookup fails,
- author disambiguation,
- institution/funder connections,
- citation networks,
- topic classification,
- “find related works” features,
- filling in missing metadata.

But aggregator records may lag, merge imperfectly, or differ from the registration agency’s deposited metadata.

### Public API vs member/authenticated API

Some services have both public and authenticated APIs.

For example:

- Crossref’s public REST API can retrieve public metadata without signup.
- DataCite’s public API can retrieve public/findable DOI metadata.
- DataCite authenticated/member APIs can create or update DOI records.
- OpenAlex has API access policies and may require an API key depending on usage/current rules.

For a personal DOI lookup CLI, public read APIs are usually enough.

### JSON

**JSON** is a common machine-readable data format.

Crossref, DataCite, and OpenAlex all provide JSON responses, but their JSON structures differ.

Your code should not assume that `title`, `authors`, `publisher`, or `date` are represented the same way across APIs.

### CSL-JSON

**CSL-JSON** is a JSON format used by Citation Style Language tools. It is often useful if your goal is formatted citations.

It may be less complete than the full native API response.

### BibTeX and RIS

**BibTeX** and **RIS** are bibliographic exchange formats.

They are useful for citation managers, but they are not ideal canonical storage formats for rich metadata because they flatten or lose some structure.

### OAI-PMH

**OAI-PMH** is a protocol for metadata harvesting, often used by repositories and aggregators.

For a small DOI lookup CLI, OAI-PMH is usually less convenient than REST APIs. For bulk harvesting, it can be important.

### GraphQL

**GraphQL** is an API query language where clients ask for specific fields and relationships.

Some scholarly infrastructure services expose GraphQL APIs for more flexible graph-style querying.

### Rate limits and polite API use

Metadata services are shared infrastructure. A good CLI should:

- send a descriptive User-Agent when requested/recommended,
- include contact information where appropriate,
- cache responses when possible,
- avoid hammering APIs,
- handle 404, 429, 5xx, and timeouts gracefully,
- distinguish “not found here” from “not a valid DOI.”

---

## 10. How a DOI lookup CLI should think

A robust DOI lookup workflow might look like this:

```text
Input DOI or DOI URL
    ↓
Normalize presentation
    ↓
Try resolver / content negotiation if you need citation output
    ↓
Try Crossref if likely scholarly-publishing DOI
    ↓
Try DataCite if Crossref misses or resource looks data/software/repository-like
    ↓
Try OpenAlex for enrichment/fallback/search
    ↓
Merge cautiously, preserving provenance
    ↓
Display a human-friendly summary
```

### Why preserve provenance?

Because the same field may differ across sources.

Example:

```text
Title from Crossref:   deposited by publisher/member
Title from DataCite:   deposited by repository/member
Title from OpenAlex:   indexed/enriched/merged from many sources
```

Your tool should know where each value came from.

A good metadata display might say:

```text
Title: Attention Is All You Need
Source: Crossref
DOI: 10.xxxx/yyyy
OpenAlex ID: W....
ORCID IDs found: ...
```

rather than pretending all data came from one universal registry.

### Suggested source hierarchy

This is not a law, but it is a sensible default:

1. **For DOI validity/resolution:** use `doi.org`.
2. **For deposited DOI metadata:** use the registration agency that owns the DOI record, often Crossref or DataCite.
3. **For citation formatting:** use content negotiation, Crossref, DataCite, or a CSL processor.
4. **For enrichment:** use OpenAlex, ORCID, ROR, Unpaywall, Semantic Scholar, etc.
5. **For full-text access / open-access locations:** consider Unpaywall or publisher/repository links, not DOI alone.

### Common failure modes

| Symptom | Possible explanation |
|---|---|
| DOI resolves in browser but Crossref returns 404 | It may be a DataCite DOI or another RA’s DOI |
| Crossref has sparse metadata | Publisher/member deposited sparse metadata |
| OpenAlex has richer data than Crossref | OpenAlex enriched from other sources |
| OpenAlex differs from Crossref | Aggregation/disambiguation lag or mismatch |
| DOI redirects to a dead page | Registrant may not have updated target URL |
| DOI exists but no PDF link appears | DOI identifies landing page/work, not necessarily free full text |
| Author names missing ORCID IDs | ORCID IDs were not deposited or linked |
| Dataset article relation missing | Related identifiers were not deposited or not harvested |

---

## 11. Common misconceptions

### “A DOI is a URL.”

Not exactly. The DOI is the identifier. `https://doi.org/...` is the web-actionable form of the identifier.

### “A DOI points to a PDF.”

Usually no. It usually points to a landing page.

### “If it has a DOI, it is open access.”

No. DOI resolution is free. Access to the content may be open, paywalled, embargoed, restricted, or unavailable.

### “Crossref is the DOI database.”

Crossref is a major DOI registration agency, but it is not the entire DOI system. DataCite and other RAs also register DOIs.

### “DataCite is only for datasets.”

DataCite is strongly associated with datasets, but it supports many research outputs/resources, including software, samples, preprints, instruments, dissertations, and more.

### “OpenAlex is the official DOI record.”

No. OpenAlex is an aggregator/index. It is often excellent, but it is not the DOI registration agency.

### “ORCID identifies papers.”

No. ORCID identifies people. Papers/resources can have DOIs; people can have ORCID iDs.

### “The publisher field always means a commercial publisher.”

No. Especially in DataCite/repository contexts, publisher can mean a repository, archive, institution, distributor, or producer.

### “Metadata is always correct because it came from an API.”

No. APIs expose metadata; they do not guarantee perfection. Metadata can be missing, stale, inconsistent, duplicated, or wrong.

---

## 12. Practical glossary

### Abstract

A summary of a work. May or may not be available in metadata APIs. Some abstracts are copyrighted or restricted.

### Affiliation

The organization associated with a person, often an author. Increasingly represented with ROR IDs.

### Author

A person credited with creating a textual scholarly work. Similar to but narrower than “creator.”

### Citation

A directed relationship where one work cites another.

### Citation count

The number of citations a service knows about. Citation counts differ across Crossref, OpenAlex, Google Scholar, Scopus, Web of Science, Semantic Scholar, etc., because their coverage and counting rules differ.

### Content negotiation

HTTP-based way to ask a DOI resolver for metadata in a preferred representation, such as CSL-JSON or BibTeX.

### Contributor

A person or organization with a role in a work/resource, not necessarily an author/creator.

### Creator

The primary creator of a resource. Common in DataCite metadata.

### Crossref

A DOI registration agency and metadata infrastructure organization, especially important for scholarly publishing.

### DataCite

A DOI registration agency and metadata infrastructure organization, especially important for datasets, software, repository objects, and diverse research outputs/resources.

### DOI

Digital Object Identifier; a persistent identifier for an object.

### DOI Foundation

The standards/governance organization for the DOI system and registration authority for the DOI ISO standard.

### DOI prefix

The part before the slash, allocated through the DOI system.

### DOI suffix

The part after the slash, chosen by the registrant within the prefix.

### DOI URL

The web-actionable DOI form, usually `https://doi.org/...`.

### Deposited metadata

Metadata submitted to a registration agency by a responsible member/registrant or trusted source.

### Enriched metadata

Metadata improved or connected by an index/aggregator after deposit.

### Full text

The actual article, dataset file, software archive, or resource content, as opposed to its metadata record.

### Handle System

The underlying identifier-resolution technology on which the DOI system is implemented.

### Identifier

A name or code that identifies something. Not necessarily a URL.

### Landing page

The human-facing page that a DOI usually resolves to.

### Metadata

Data describing a work/resource/person/organization.

### Metadata schema

Rules and fields defining how metadata is structured.

### OpenAlex

An open scholarly metadata index/graph and API; useful for discovery and enrichment, but not a DOI registration agency.

### ORCID

Open Researcher and Contributor ID; a persistent identifier for people.

### PID

Persistent identifier.

### Publisher

An overloaded term: may mean the publishing organization, a metadata field, a repository/institution, or the party responsible for issuing/distributing a resource.

### Registrant

The person or organization that registers a DOI with a registration agency and is responsible for maintaining the DOI record.

### Registration agency

An organization authorized within the DOI system to register DOI names and provide related metadata services.

### Resolution

The act of using an identifier to retrieve or access something useful, such as a redirect target or metadata representation.

### Resolver

A service that performs resolution. For DOI URLs, this is usually `doi.org`.

### Resource

A broad term for the thing identified/described, especially in DataCite contexts.

### REST API

An HTTP API organized around URLs/resources and usually returning JSON.

### ROR

Research Organization Registry; persistent identifiers for organizations.

### Source

A venue/container/repository/journal/conference where a work appears. In OpenAlex, “source” is a formal entity type.

### Target URL

The current URL stored behind a DOI, usually a landing page.

### Work

A scholarly output or research object: article, dataset, software release, book chapter, report, dissertation, preprint, etc.

---

## 13. Recommended mental model for your DOI/metadata tool

For code design, do not name things as if there is one universal “DOI metadata API.”

A clearer internal model is:

```text
DoiInput
    raw string from user

NormalizedDoi
    clean DOI name, e.g. 10.xxxx/yyyy

ResolvedDoi
    result of asking doi.org where it goes

CrossrefWork
    Crossref's metadata record, if Crossref knows it

DataCiteDoi
    DataCite's metadata record, if DataCite knows it

OpenAlexWork
    OpenAlex's aggregated/enriched work record, if OpenAlex knows it

MergedMetadata
    your app's carefully combined display object
```

That makes it easier to avoid conceptual bugs such as:

- treating OpenAlex as the DOI registrar,
- treating Crossref as if it knows all DOIs,
- assuming every DOI is article-like,
- assuming every `publisher` field means the same thing,
- flattening person identifiers and work identifiers together,
- losing which source supplied which field.

### Suggested display fields

For a human-facing CLI summary, useful fields might include:

```text
DOI
Title
Type / resource type
Year / publication date
Authors / creators
ORCID IDs, if present
Publisher / repository / source
Venue / source / container
Landing page / target URL
Registration agency source used
OpenAlex ID, if found
DataCite / Crossref record URL
License
Related identifiers
References count / citations count, with source named
Metadata source provenance
```

### Suggested source labels

Use explicit labels such as:

```text
crossref.title
datacite.attributes.titles
openalex.display_name
doi_org.resolved_url
```

rather than immediately merging them into anonymous fields.

---

## 14. Sources and further reading

Primary/reference sources used for this guide:

- [DOI Foundation — What is a DOI?](https://www.doi.org/the-identifier/what-is-a-doi)
- [DOI Foundation — About Us](https://www.doi.org/the-foundation/about-us/)
- [DOI Foundation — What are Registration Agencies?](https://www.doi.org/the-community/what-are-registration-agencies/)
- [DOI Foundation — Existing Registration Agencies](https://www.doi.org/the-community/existing-registration-agencies/)
- [DOI Content Negotiation documentation](https://citation.doi.org/docs.html)
- [Crossref — Content Registration](https://www.crossref.org/services/content-registration/)
- [Crossref — REST API documentation](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)
- [DataCite — Create DOIs](https://datacite.org/create-dois/)
- [DataCite — REST API guide](https://support.datacite.org/docs/api)
- [DataCite — Metadata Schema](https://schema.datacite.org/)
- [DataCite Metadata Schema — Publisher property](https://datacite-metadata-schema.readthedocs.io/en/4.5/properties/publisher/)
- [ORCID — For Researchers](https://info.orcid.org/researchers/)
- [ORCID — About ORCID](https://info.orcid.org/what-is-orcid/)
- [OpenAlex Developers — Overview](https://developers.openalex.org/)
- [OpenAlex — About the Data](https://help.openalex.org/hc/en-us/articles/24397285563671-About-the-data)
- [OpenAlex — How does OpenAlex work?](https://help.openalex.org/hc/en-us/articles/28932712154391-How-does-OpenAlex-work)
