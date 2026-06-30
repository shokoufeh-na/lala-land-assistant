# -------streamlit run app.py-------
# -------Includes two reasoned protégé lala-land-reasoned.owl and not reasoned lala-land-rdf.owl------
# -------I did not update app.py with reasoned protoge-------
# -------Instances are loaded and read from graph , not ontology--------

import streamlit as st
from rdflib import Graph, Namespace
from rdflib.namespace import RDF, XSD
import re

# -----------------------------
# Load Graph
# -----------------------------
@st.cache_resource
def load_graph():
    g = Graph()
    g.parse("lala-land-rdf.owl", format="xml")       # ontology
    g.parse("instances.ttl", format="turtle")        # individuals
    return g

g = load_graph()
LA = Namespace("http://example.com/lala-land#")

st.set_page_config(page_title="LA Neighborhoods Q&A", layout="centered")
st.title("LA Neighborhoods — Q&A (Streamlit)")
st.caption("Ask questions like: *Where do rich residents live?*, *Creative neighborhoods?*, *Ocean view homes?*")

question = st.text_input("Ask a question", "")

# -----------------------------
# SPARQL Query Helpers
# -----------------------------

def answer_ocean_view(graph):
    q = """
    SELECT DISTINCT ?area ?feature WHERE {
      ?area <http://example.com/lala-land#features> ?feature .
      FILTER(CONTAINS(LCASE(STR(?feature)), "ocean"))
    }
    """
    return [(str(r.area).split('#')[-1], str(r.feature)) for r in graph.query(q)]

def answer_price_gt_5m(graph):
    q = """
    SELECT DISTINCT ?area ?price WHERE {
      ?area <http://example.com/lala-land#hasAvgPrice> ?price .
      FILTER(xsd:decimal(?price) > 5000000)
    } ORDER BY DESC(xsd:decimal(?price))
    """
    return [(str(r.area).split('#')[-1], float(r.price)) for r in graph.query(q)]

def answer_fine_dining(graph):
    q = """
    SELECT DISTINCT ?area ?cuisine WHERE {
      ?area <http://example.com/lala-land#knownForCuisine> ?cuisine .
      FILTER(CONTAINS(LCASE(STR(?cuisine)), "fine dining"))
    }
    """
    return [(str(r.area).split('#')[-1], str(r.cuisine)) for r in graph.query(q)]

def describe_beverly_hills(graph):
    q = """
    SELECT ?desc ?price ?vibe WHERE {
      <http://example.com/lala-land#beverlyHills>
         <http://example.com/lala-land#description> ?desc ;
         <http://example.com/lala-land#hasAvgPrice> ?price ;
         <http://example.com/lala-land#hasVibe> ?vibe .
    }
    """
    return list(graph.query(q))

def answer_rich(graph):
    """Neighborhoods with avg price > $3M."""
    q = """
    SELECT DISTINCT ?area ?price WHERE {
      ?area <http://example.com/lala-land#hasAvgPrice> ?price .
      FILTER(xsd:decimal(?price) > 3000000)
    } ORDER BY DESC(xsd:decimal(?price))
    """
    return [(str(r.area).split('#')[-1], float(r.price)) for r in graph.query(q)]

def answer_celebrity(graph):
    q = """
    SELECT DISTINCT ?area WHERE {
      ?area <http://example.com/lala-land#hasCelebrityResidents> "true"^^xsd:boolean .
    }
    """
    return [str(r.area).split('#')[-1] for r in graph.query(q)]

def answer_creative(graph):
    """Creative / Arts neighborhoods."""
    q = """
    SELECT DISTINCT ?area ?tag WHERE {
      { ?area <http://example.com/lala-land#knownForArts> ?tag }
      UNION
      { ?area <http://example.com/lala-land#knownForCulture> ?tag }
      UNION
      { ?area a <http://example.com/lala-land#CreativeHotspot> }
    }
    """
    results = []
    for r in graph.query(q):
        area = str(r.area).split('#')[-1]
        if hasattr(r, "tag") and r.tag:
            tag = str(r.tag)
        else:
            tag = "CreativeHotspot"
        results.append((area, tag))
    return results

def answer_academic(graph):
    q = """
    SELECT DISTINCT ?area ?vibe WHERE {
      ?area <http://example.com/lala-land#hasVibe> ?vibe .
      FILTER(CONTAINS(LCASE(STR(?vibe)), "academic"))
    }
    """
    return [(str(r.area).split('#')[-1], str(r.vibe)) for r in graph.query(q)]

def answer_gated(graph):
    q = """
    SELECT DISTINCT ?area ?feature WHERE {
      ?area <http://example.com/lala-land#features> ?feature .
      FILTER(CONTAINS(LCASE(STR(?feature)), "gated"))
    }
    """
    return [(str(r.area).split('#')[-1], str(r.feature)) for r in graph.query(q)]

def answer_nightlife(graph):
    q = """
    SELECT DISTINCT ?area ?feature WHERE {
      ?area <http://example.com/lala-land#features> ?feature .
      FILTER(CONTAINS(LCASE(STR(?feature)), "nightlife"))
    }
    """
    return [(str(r.area).split('#')[-1], str(r.feature)) for r in graph.query(q)]

def answer_luxury(graph):
    """Identify luxury neighborhoods and explain why."""
    q = """
    SELECT DISTINCT ?area ?price ?vibe ?desc ?type WHERE {
      ?area <http://example.com/lala-land#hasAvgPrice> ?price ;
            <http://example.com/lala-land#hasVibe> ?vibe ;
            <http://example.com/lala-land#description> ?desc ;
            rdf:type ?type .
      FILTER(xsd:decimal(?price) > 3000000)
    }
    """
    results = []
    for r in graph.query(q):
        area = str(r.area).split('#')[-1]
        price = float(r.price)
        vibe = str(r.vibe)
        desc = str(r.desc)
        type_uri = str(r.type).split('#')[-1]
        # classify luxury type
        if "CoastalLuxuryNeighborhood" in type_uri:
            lux_type = "Coastal Luxury"
        elif "ExclusiveResidentialNeighborhood" in type_uri:
            lux_type = "Celebrity Luxury"
        elif "UrbanLuxuryNeighborhood" in type_uri and "historic" in desc.lower():
            lux_type = "Historic Luxury"
        else:
            lux_type = "General Luxury"
        results.append((area, price, vibe, desc, lux_type))
    return results

# -----------------------------
# Intent Detection Engine
# -----------------------------
def answer_free_text(text, graph):
    text = text.lower().strip()

    # ---- OCEAN VIEW ----
    if re.search(r"\bocean\b|\bocean[- ]?view\b", text):
        res = answer_ocean_view(graph)
        if not res:
            return "No ocean-view neighborhoods found."
        names = [r[0] for r in res]
        if "malibu" in [n.lower() for n in names]:
            return "Malibu"
        return ", ".join(names)

    # ---- VERY EXPENSIVE (>$5M) ----
    if re.search(r"(>|\bover\b|\bmore than\b).*5 ?m|\b5,?000,?000\b|\b5m\b", text):
        res = answer_price_gt_5m(graph)
        if not res:
            return "No neighborhoods found with prices > $5M."
        return ", ".join([f"{n} (${int(p):,})" for n, p in res])

    # ---- RICH RESIDENTS ----
    if re.search(r"\brich\b|\bwealthy\b|\baffluent\b|\bhigh price\b|\bexpensive\b", text):
        res = answer_rich(graph)
        if not res:
            return "No rich/affluent neighborhoods found."
        return ", ".join([f"{n} (${int(p):,})" for n, p in res])

    # ---- CELEBRITY HOTSPOTS ----
    if re.search(r"\bcelebrity\b|\bcelebrities\b|\bceleb\b|\bcelebs\b|\bfamous\b", text):
        res = answer_celebrity(graph)
        if not res:
            return "No celebrity neighborhoods found."
        return ", ".join(res)

    # ---- CREATIVE / ARTS ----
    if re.search(r"\bcreative\b|\bartist(?:s)?\b|\barts?\b|\bmusician(?:s)?\b|\bbohemian\b", text):
        res = answer_creative(graph)
        if not res:
            return "No creative neighborhoods found."
        return ", ".join([f"{n} ({tag})" for n, tag in res])

    # ---- FINE DINING ----
    if re.search(r"\bfine dining\b|\bmichelin\b", text):
        res = answer_fine_dining(graph)
        if not res:
            return "No fine dining neighborhoods found."
        return ", ".join([f"{name} ({cuisine})" for name, cuisine in res])

    # ---- BEVERLY HILLS ----
    if "beverly" in text:
        rows = describe_beverly_hills(graph)
        if not rows:
            return "No details found for Beverly Hills."
        desc, price, vibe = rows[0]
        return f"Description: {desc}\nAvg price: ${int(float(price)):,}\nVibe: {vibe}"

    # ---- ACADEMIC ----
    if re.search(r"\bacademic\b|\bcollege\b|\buniversity\b", text):
        res = answer_academic(graph)
        if res:
            return ", ".join([f"{n} ({v})" for n, v in res])
        else:
            return "No academic neighborhoods found."
   
    # ---- Gated Community ----
    if re.search(r"\bgated\b|\bgated community\b", text):
      res = answer_gated(graph)
      if res:
        return ", ".join([f"{n} ({f})" for n, f in res])
      else:
        return "No gated communities found."

    # ---- NIGHT LIFE ----
    if re.search(r"\bnightlife\b|\bparty\b", text):
        res = answer_nightlife(graph)
        if res:
            return ", ".join([f"{n} ({f})" for n, f in res])
        else:
            return "No nightlife neighborhoods found."

    # ---- LUXURY AREAS ----
    if re.search(r"\bluxury\b|\bexpensive areas\b|\bhigh-end\b", text):
       res = answer_luxury(graph)
       if res:
         return "\n".join([
            f"{n} (${int(p):,}) — {lux_type}. Vibe: {vibe}. Why: {desc}"
            for n, p, vibe, desc, lux_type in res
        ])
       else:
         return "No luxury neighborhoods found."


    # ---- DEFAULT ----
    return "Sorry — I don't understand that question yet."

# -----------------------------
# UI
# -----------------------------
if st.button("Get Answer") and question.strip():
    with st.spinner("Thinking..."):
        ans = answer_free_text(question, g)
    st.subheader("Answer")
    if isinstance(ans, str) and "\n" in ans:
        st.text(ans)
    else:
        st.markdown(f"**{ans}**")
elif question.strip():
    st.info("Type your question and click **Get Answer**.")

# Debug Panel
with st.expander("Show raw triples & prefixes (debug)"):
    st.write("Total triples:", len(g))
    st.write("Namespaces:", list(g.namespaces()))
