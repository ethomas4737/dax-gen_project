"""Build combined dataset variants D1-D4 from the curated Phase 1 rawdata.

D1 = D-SCRIPT PPI, all species/splits, unified to (seq_a, seq_b, label).
D2 = AVIDa (no COVID: hIL6 + hTNFa), unified to (seq_a=VHH, seq_b=antigen, label).
D3 = D1 union D2, common schema, tagged by pair_type/source_dataset.
D4 = D3 as the training pool; MLAEP reframed as a held-out eval partition
     (RBD mutant seq, human ACE2 seq, ace2_bind label) - NOT merged into D3.
     Also includes an 8-antibody escape panel (RBD mutant, antibody VH/VL,
     binds label) sourced from CoV-AbDab (VH/VL originally from Zost et al.
     2020, Nature Medicine).

Writes to rawdata/combined/{d1_ppi.csv, d2_avida.csv, d3_ppi_avida.csv,
d4_heldout_mlaep_ace2.csv, d4_heldout_mlaep_antibodies.csv} plus SOURCE.md.
"""
import pandas as pd
from pathlib import Path

RAWDATA = Path("rawdata")
OUT = RAWDATA / "combined"
OUT.mkdir(parents=True, exist_ok=True)

HUMAN_ACE2_SEQ = (
    "MSSSSWLLLSLVAVTAAQSTIEEQAKTFLDKFNHEAEDLFYQSSLASWNYNTNITEENVQ"
    "NMNNAGDKWSAFLKEQSTLAQMYPLQEIQNLTVKLQLQALQQNGSSVLSEDKSKRLNTIL"
    "NTMSTIYSTGKVCNPDNPQECLLLEPGLNEIMANSLDYNERLWAWESWRSEVGKQLRPLY"
    "EEYVVLKNEMARANHYEDYGDYWRGDYEVNGVDGYDYSRGQLIEDVEHTFEEIKPLYEHL"
    "HAYVRAKLMNAYPSYISPIGCLPAHLLGDMWGRFWTNLYSLTVPFGQKPNIDVTDAMVDQ"
    "AWDAQRIFKEAEKFFVSVGLPNMTQGFWENSMLTDPGNVQKAVCHPTAWDLGKGDFRILM"
    "CTKVTMDDFLTAHHEMGHIQYDMAYAAQPFLLRNGANEGFHEAVGEIMSLSAATPKHLKS"
    "IGLLSPDFQEDNETEINFLLKQALTIVGTLPFTYMLEKWRWMVFKGEIPKDQWMKKWWEM"
    "KREIVGVVEPVPHDETYCDPASLFHVSNDYSFIRYYTRTLYQFQFQEALCQAAKHEGPLH"
    "KCDISNSTEAGQKLFNMLRLGKSEPWTLALENVVGAKNMNVRPLLNYFEPLFTWLKDQNK"
    "NSFVGWSTDWSPYADQSIKVRISLKSALGDKAYEWNDNEMYLFRSSVAYAMRQYFLKVKN"
    "QMILFGEEDVRVANLKPRISFNFFVTAPKNVSDIIPRTEVEKAIRMSRSRINDAFRLNDN"
    "SLEFLGIQPTLGPPNQPPVSIWLIVFGVVMGVIVVGIVILIFTGIRDRKKKNKARSGENP"
    "YASIDISKGENNPGFQNTDDVQTSF"
)  # UniProt Q9BYF1, canonical, fetched 2026-07-09

# 8-antibody escape panel from MLAEP's GMM_covid_info_seq.csv COV2-*_400 columns.
# VH/VL sourced from CoV-AbDab (opig.stats.ox.ac.uk/webapps/covabdab), which cites
# Seth Zost et al., 2020 (Nature Medicine, https://www.nature.com/articles/s41591-020-0998-x)
# as the origin. seq_b = VH + "/" + VL (explicit non-AA separator marking the chain
# boundary - VH and VL are two separate polypeptide chains, not a real fused construct).
ANTIBODY_VH_VL = {
    "COV2-2050": ("QVQLVQSGAEVKKPGASVKVSCKASGYTFTDYYMHWVRQAPGQGLEWMGWINPNSRGTNYAQKFQGRVTMTRDTSISTVYMELSRLTSDDTAVYYCARVVVLGYGRPNNYYDGRNVWDYWGQGTLVTVSS",
                  "QSVLTQPPSASGTPGQRVIISCSGSSSNIGSNTVKWYHQLPGTAPKLLICSNNQRPSGVPDRFSGSKSDTSASLAISGLQSEDEADYYCAAWDDSLNALVFGGGTKLTVL"),
    "COV2-2096": ("QVQLVQSGAEVKKPGASVKVSCKASGYTFGSFDINWVRQATGQGLEWMGRMNSNSGNTAYAQKFQGRVTMTRDTSTNTAYMELSSLRSEDTAMYYCARMRSGWPTHGRPDDFWGRGTLVTVSS",
                  "QSVLTQAPSASGTPGQRVTISCSGSNSNIGSYTINWYQQLPGTAPKLLIYGNDQRTSGVPDRFSGSKFGTSASLAISGLQSEDENNYYCAVWDDSLNGLVFGGGTKLTVL"),
    "COV2-2094": ("EVQLVESGGGVVRPGGSLRLSCAASGFIFDDYDMTWVRQAPGKGLEWVSGINWNGGSTGYADSVKGRFTISRDNAKNSLYLQMNSLRAEDTALYHCAVIMSPIPRYSGYDWAGDAFDIWGQGTMVTVSS",
                  "SSELTQDPAVSVALGQTVRITCQGDSLRSYYASWYQQKPGQVPILVIYDKNNRPSGIPDRFSGSSSGNTASLTITGAQAEDEADYYCNSRDSSGNAVVFGGGTKLTVL"),
    "COV2-2677": ("QLQLQESGPGLVKPSETLSLTCTVSGGSISSSSYYWGWIRQPPGKGLEWIGSMYYSGSTYYNPSLKSRVTISVDTSKNQFSLKLSSVTAADTAVYYCARLLWLRGHFDYWGQGTLVTVSS",
                  "NFMLTQPHSVSESPGKTVTISCTGSSGSIASNYVQWYQQRPGSAPTTVIYEDNQRPSGVPDRFSGSIDSSSNSASLTISGLKTEDEADYYCQSYDSSNYWVFGGGTKLTVL"),
    "COV2-2479": ("QVQLVQSGAEVKKPGSSVKVSCKTSGDTSSSYTVGWVRQAPGQGLEWMGRIIPILGIAYSAQKFQGRLTITADKSTSTSYMELSSLRSEDTAVYYCARGVVAATPGWFDPWGQGTLVTVSS",
                  "EIVMTQSPATLSVSPGERVTLSCRASQSVSSNLAWYQQKPGQAPRLLIYGASTRATGIPARFSGGGSGTEFTLTISSLQSEDFAVYYCQQYNNFLTFGGGTKVEIK"),
    "COV2-2165": ("EVQLVESGGGLVQPGGSLRLSCAASGLTVRSNYMTWVRQTPGKGLEWVSVIYSGGSTFYADSVKGRFTISRDNSKNTVYLQMNSLRAEDTAVYYCARDLVTYGLDVWGQGTTVTVSS",
                  "DIQLTQSPSFLSASVGDRVTITCRASQGISNYLAWYQQKPGTAPNLLIYAASTLQSGVPSRFSGSGSGTEFTLTISSLQPEDFATYYCQLLNSHPLTFGQGTRLEIK"),
    "COV2-2499": ("QLQLQESGPGLVKPSETLSLTCTVSGGSVSSRSYYWGWIRQPPGKGLEWIGSIYYSGSTYYNPSLKSRVTISVDTSKNQFSLKLSSVTAADTAVYYCARHTVDCGGDCFPNDAFDIWGQGTMVTVSS",
                  "SSELTQDPAVSVALGQTVRITCQGDSLRSYYASWYQQKPGQAPLLVIYGKNNRPSGIPDRFSGSSSGNTPSLTITGAQAEDEADYYCNFRDSSGHHPVFGEGTKLTVL"),
    "COV2-2832": ("EVQLVESGGGLVQPGGSLRLSCAASGLTVSSNYMSWVRQAPGKGLECVSVIYAGGNTYYADSVKGRFTISRDNSKNTLYLQMNSLRAEDTAVYYCARGDGGYYSPFDYWGQGTLVTVSS",
                  "DIQMTQSPSSLSASVGDRVTITCRASQSISSYLNWYQQKPGKAPKVLIYAASTMQSGVPSRFRGSGSGTDFTLTISSLQLEDFATYYCQQSYSTPQTFGQGTKVEIK"),
}


def read_fasta(path):
    seqs = {}
    cur_id, cur_seq = None, []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith(">"):
                if cur_id:
                    seqs[cur_id] = "".join(cur_seq)
                cur_id, cur_seq = line[1:], []
            else:
                cur_seq.append(line)
        if cur_id:
            seqs[cur_id] = "".join(cur_seq)
    return seqs


def read_pairs(path):
    df = pd.read_csv(path, sep="\t", header=None, names=["protein_a", "protein_b", "label"])
    df["label"] = df["label"].astype(float).astype(int)
    return df


def build_d1():
    species_files = {
        "human": [("human_train", "pairs/human_train.tsv"), ("human_test", "pairs/human_test.tsv")],
        "mouse": [("mouse_test", "pairs/mouse_test.tsv")],
        "fly": [("fly_test", "pairs/fly_test.tsv")],
        "yeast": [("yeast_test", "pairs/yeast_test.tsv")],
        "worm": [("worm_test", "pairs/worm_test.tsv")],
        "ecoli": [("ecoli_test", "pairs/ecoli_test.tsv")],
    }
    rows = []
    for species, files in species_files.items():
        seqs = read_fasta(RAWDATA / "ppi" / "seqs" / f"{species}.fasta")
        for source_dataset, rel in files:
            df = read_pairs(RAWDATA / "ppi" / rel)
            df["seq_a"] = df["protein_a"].map(seqs)
            df["seq_b"] = df["protein_b"].map(seqs)
            df["species"] = species
            df["source_dataset"] = f"dscript_{source_dataset}"
            rows.append(df[["seq_a", "seq_b", "label", "species", "source_dataset", "protein_a", "protein_b"]])
    d1 = pd.concat(rows, ignore_index=True)
    d1["pair_type"] = "ppi"
    n_missing = d1["seq_a"].isna().sum() + d1["seq_b"].isna().sum()
    assert n_missing == 0, f"{n_missing} unresolved protein IDs in D1"
    return d1


def build_d2():
    rows = []
    for name, pairs_file, antigen_file in [
        ("hIL6", "AVIDa-hIL6.csv", "hIL6_antigen_sequences.csv"),
        ("hTNFa", "AVIDa-hTNFa.csv", "hTNFa_antigen_sequences.csv"),
    ]:
        pairs = pd.read_csv(RAWDATA / "avida" / pairs_file)
        antigens = pd.read_csv(RAWDATA / "avida" / antigen_file)
        merged = pairs.merge(antigens, on="Ag_label", how="left")
        assert merged["Ag_sequence"].isna().sum() == 0, f"unresolved antigen labels in {name}"
        merged = merged.rename(columns={"VHH_sequence": "seq_a", "Ag_sequence": "seq_b"})
        merged["source_dataset"] = f"avida_{name.lower()}"
        rows.append(merged[["seq_a", "seq_b", "label", "Ag_label", "source_dataset"]])
    d2 = pd.concat(rows, ignore_index=True)
    d2["pair_type"] = "antibody_antigen"
    return d2


def build_d3(d1, d2):
    common_cols = ["seq_a", "seq_b", "label", "pair_type", "source_dataset"]
    d3 = pd.concat([d1[common_cols], d2[common_cols]], ignore_index=True)
    return d3


def build_d4_heldout():
    gmm = pd.read_csv(RAWDATA / "mlaep" / "GMM_covid_info_seq.csv", index_col=0)
    d4h = pd.DataFrame({
        "seq_a": gmm["seq"],
        "seq_b": HUMAN_ACE2_SEQ,
        "label": gmm["ace2_bind"],
        "aa_substitutions": gmm["aa_substitutions"],
        "avg_bind_score": gmm["avg_bind"],
    })
    d4h["pair_type"] = "viral_receptor"
    d4h["source_dataset"] = "mlaep_ace2_heldout"
    return d4h


def build_d4_heldout_antibodies():
    gmm = pd.read_csv(RAWDATA / "mlaep" / "GMM_covid_info_seq.csv", index_col=0)
    rows = []
    for ab_name, (vh, vl) in ANTIBODY_VH_VL.items():
        col = f"{ab_name}_400"
        assert col in gmm.columns, f"missing column {col} in GMM_covid_info_seq.csv"
        df = pd.DataFrame({
            "seq_a": gmm["seq"],
            "seq_b": f"{vh}/{vl}",
            "label": 1 - gmm[col],  # flip: MLAEP's column is "escapes" (1=no binding); we want 1=binds
            "aa_substitutions": gmm["aa_substitutions"],
            "antibody": ab_name,
        })
        df["source_dataset"] = f"mlaep_{ab_name.lower()}_heldout"
        rows.append(df)
    d4ab = pd.concat(rows, ignore_index=True)
    d4ab["pair_type"] = "antibody_antigen"
    return d4ab


def main():
    d1 = build_d1()
    d1.to_csv(OUT / "d1_ppi.csv", index=False)
    print(f"D1 (PPI): {len(d1):,} rows -> {OUT/'d1_ppi.csv'}")

    d2 = build_d2()
    d2.to_csv(OUT / "d2_avida.csv", index=False)
    print(f"D2 (AVIDa): {len(d2):,} rows -> {OUT/'d2_avida.csv'}")

    d3 = build_d3(d1, d2)
    d3.to_csv(OUT / "d3_ppi_avida.csv", index=False)
    print(f"D3 (D1+D2): {len(d3):,} rows -> {OUT/'d3_ppi_avida.csv'}")

    d4h = build_d4_heldout()
    d4h.to_csv(OUT / "d4_heldout_mlaep_ace2.csv", index=False)
    print(f"D4 held-out (MLAEP/ACE2): {len(d4h):,} rows -> {OUT/'d4_heldout_mlaep_ace2.csv'}")

    d4ab = build_d4_heldout_antibodies()
    d4ab.to_csv(OUT / "d4_heldout_mlaep_antibodies.csv", index=False)
    print(f"D4 held-out (MLAEP/8-antibody panel): {len(d4ab):,} rows -> {OUT/'d4_heldout_mlaep_antibodies.csv'}")

    print("D4 train pool = D3 (rawdata/combined/d3_ppi_avida.csv); no separate file duplicated.")


if __name__ == "__main__":
    main()
