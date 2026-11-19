// =====================================================================
// Snippet browser untuk penyedia.inaproc.id (jalankan di DevTools Console
// pada tab yang SUDAH LOGIN, mis. https://penyedia.inaproc.id/products/add).
// Menghasilkan file JSON berisi status kelayakan KBLI untuk semua kategori.
// =====================================================================

const gq = async (query, variables) => {
  const r = await fetch('/graphql', {
    method: 'POST', credentials: 'include',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query, variables }),
  });
  const t = await r.text();
  if (!r.ok || t[0] === '<') {
    const e = new Error('HTTP ' + r.status);
    e.status = r.status; e.retry = r.headers.get('retry-after');
    throw e;
  }
  return JSON.parse(t);
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const Q_TREE = `query($input: AllMinifiedProductCategoryInput!){ allMinifiedProductCategory(input:$input){
  ... on AllMinifiedProductCategories{ items{ id name level productType parentId
    children{ id name level productType parentId children{ id name level productType parentId } } } } } }`;
const Q_CAT = `query($id: ID!){ getProductCategory(id:$id){ ... on ProductCategory{
  id name kbli kbliCodes{ code version } curationEnabled productType } } }`;
const Q_INST = `query($id: String!){ getInstitutionByID(id:$id){ ... on Institution{
  company{ oss{ project: projectV2{ kbli{ kbli name versi } } } } } } }`;
const Q_KBLI = `query($codes:[String],$versionedCodes:[KBLIVersionedCodeInput!],$perPage:Int,$page:Int){
  getAllKBLI(codes:$codes, versionedCodes:$versionedCodes, perPage:$perPage, page:$page){
    total lastPage items{ code title classification } } }`;
const Q_PRODUCTS = `query($page:Int,$perPage:Int,$filter:ListProductFilterInput){
  listProduct(query:{pagination:{page:$page,perPage:$perPage},filter:$filter}){
    ... on ListProductRes{ total lastPage items{ id name status category{ id name } } } } }`;

async function runKbliCheck() {
  const session = await (await fetch('/api/auth/session', { credentials: 'include' })).json();
  const institutionId = session.user.institutionId;

  // 1) KBLI perusahaan
  const inst = await gq(Q_INST, { id: institutionId });
  const seller = new Map();
  inst.data.getInstitutionByID.company.oss.project.forEach((p) =>
    (p.kbli || []).forEach((k) => seller.set(`${k.kbli}|${k.versi}`, k.name)));

  // 2) Pohon kategori
  const tree = (await gq(Q_TREE, { input: {} })).data.allMinifiedProductCategory.items;
  const leaves = [];
  tree.forEach((a) => (a.children || []).forEach((b) => (b.children || []).forEach((c) =>
    leaves.push({ id: c.id, l1: a.name, l2: b.name, l3: c.name, productType: c.productType }))));

  // 3) KBLI per kategori (2 worker, tangani 429)
  let i = 0;
  const worker = async () => {
    while (i < leaves.length) {
      const leaf = leaves[i++];
      for (let t = 0; t < 8; t++) {
        try {
          const c = (await gq(Q_CAT, { id: leaf.id })).data.getProductCategory;
          leaf.kbliCodes = (c.kbliCodes || []).map((x) => `${x.code}|${x.version}`);
          leaf.curationEnabled = c.curationEnabled;
          leaf.matched = leaf.kbliCodes.filter((k) => seller.has(k));
          leaf.status = leaf.matched.length ? 'Bisa' : 'Tidak Bisa';
          break;
        } catch (e) {
          await sleep(e.status === 429 ? ((+e.retry || 30) * 1000 + 500) : 2000);
        }
      }
      await sleep(150);
      if (i % 200 === 0) console.log('progress', i, '/', leaves.length);
    }
  };
  await Promise.all([worker(), worker()]);

  // 4) Produk existing
  const prods = (await gq(Q_PRODUCTS, { page: 1, perPage: 500, filter: {} })).data.listProduct.items;

  const out = { generatedAt: new Date().toISOString(), institutionId,
    sellerKbli: [...seller].map(([k, name]) => ({ code: k.split('|')[0], version: k.split('|')[1], name })),
    categories: leaves, products: prods };
  const blob = new Blob([JSON.stringify(out)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'inaproc_kbli_check.json'; a.click();
  console.log('Selesai:', leaves.filter((l) => l.status === 'Bisa').length, 'bisa dari', leaves.length);
}

// runKbliCheck();
