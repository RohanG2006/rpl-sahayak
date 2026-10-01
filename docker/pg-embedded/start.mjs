// Local-dev PostgreSQL launcher (no Docker / no system install needed).
// Data dir: backend/.pgdata  ·  Port: PGPORT or 5433  ·  user/pass: rpl / rpl  ·  db: rpl_sahayak
import EmbeddedPostgres from 'embedded-postgres';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const dataDir = path.resolve(here, '../../backend/.pgdata');
const port = Number(process.env.PGPORT || 5433);
const pg = new EmbeddedPostgres({
  databaseDir: dataDir, user: 'rpl', password: 'rpl', port, persistent: true,
  initdbFlags: ['--encoding=UTF8', '--locale=C'],  // UTF-8 required for Hindi text and symbols in QF data
});

const fresh = !existsSync(path.join(dataDir, 'PG_VERSION'));
if (fresh) await pg.initialise();
await pg.start();
if (fresh) await pg.createDatabase('rpl_sahayak');
if (process.argv.includes('--test-db')) { try { await pg.createDatabase('rpl_sahayak_test'); } catch {} }
console.log(`PostgreSQL ready on port ${port} (data: ${dataDir})`);
const stop = async () => { await pg.stop(); process.exit(0); };
process.on('SIGINT', stop); process.on('SIGTERM', stop);
