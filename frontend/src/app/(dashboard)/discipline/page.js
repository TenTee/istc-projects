'use client';

/**
 * Discipline : sanctions des étudiants (avertissement, blâme, exclusions).
 * Lecture : accès Étudiants (ou Pédagogie / Finance). Actions : droit Étudiants en écriture.
 */
import React from 'react';
import {
  Alert,
  Box,
  Button,
  Card,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  InputAdornment,
  MenuItem,
  Paper,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import LockOpenIcon from '@mui/icons-material/LockOpen';
import UndoIcon from '@mui/icons-material/Undo';
import SearchIcon from '@mui/icons-material/Search';
import WhatsAppIcon from '@mui/icons-material/WhatsApp';
import GavelIcon from '@mui/icons-material/Gavel';
import { etudiantsService, sanctionsService } from '../../../services/api/services';
import { getApiErrorMessage } from '../../../services/api/client';
import { useUserPermissions } from '../../../utils/permissions';
import { ConfigContext } from '../../../theme/ThemeRegistry';
import {
  COULEURS_TYPE,
  ETATS,
  LeverSanctionDialog,
  SanctionFormDialog,
  TYPES_SANCTION,
  dateFr,
  lienWhatsAppParent,
  periodeSanction,
} from '../../../components/discipline/SanctionDialogs';

const toList = (data) => (Array.isArray(data) ? data : data?.results || []);

function Chiffre({ titre, valeur, couleur }) {
  return (
    <Card variant="outlined" sx={{ p: 2, borderRadius: 2, height: '100%' }}>
      <Typography variant="caption" color="text.secondary">{titre}</Typography>
      <Typography variant="h5" fontWeight="bold" color={couleur || 'text.primary'}>{valeur ?? '-'}</Typography>
    </Card>
  );
}

export default function DisciplinePage() {
  const { canWrite } = useUserPermissions();
  const peutAgir = canWrite('can_manage_etudiants');
  const config = React.useContext(ConfigContext);

  const [sanctions, setSanctions] = React.useState([]);
  const [stats, setStats] = React.useState(null);
  const [etudiants, setEtudiants] = React.useState([]);
  const [chargement, setChargement] = React.useState(true);
  const [erreur, setErreur] = React.useState('');
  const [filtres, setFiltres] = React.useState({ q: '', type: '', etat: '' });
  const [page, setPage] = React.useState(0);
  const [parPage, setParPage] = React.useState(20);
  const [formulaire, setFormulaire] = React.useState({ open: false, sanction: null });
  const [levee, setLevee] = React.useState(null);
  const [suppression, setSuppression] = React.useState(null);
  const [toast, setToast] = React.useState({ open: false, message: '', severity: 'success' });

  const charger = React.useCallback(async () => {
    setChargement(true);
    setErreur('');
    try {
      const [liste, chiffres] = await Promise.all([sanctionsService.list(), sanctionsService.statistiques()]);
      setSanctions(toList(liste));
      setStats(chiffres);
    } catch (e) {
      setErreur(getApiErrorMessage(e, 'Chargement des sanctions impossible.'));
    } finally {
      setChargement(false);
    }
  }, []);

  React.useEffect(() => {
    const timer = setTimeout(() => {
      charger();
      etudiantsService.list().then((d) => setEtudiants(toList(d))).catch(() => setEtudiants([]));
    }, 0);
    return () => clearTimeout(timer);
  }, [charger]);

  const filtrees = React.useMemo(() => {
    const q = filtres.q.trim().toLowerCase();
    return sanctions.filter((s) => {
      if (filtres.type && s.type_sanction !== filtres.type) return false;
      if (filtres.etat && s.etat !== filtres.etat) return false;
      if (!q) return true;
      return [s.etudiant_nom, s.etudiant_matricule, s.motif, s.classe_nom].some((v) => (v || '').toLowerCase().includes(q));
    });
  }, [sanctions, filtres]);

  const visibles = filtrees.slice(page * parPage, page * parPage + parPage);
  const changerFiltre = (champ) => (e) => {
    setFiltres((f) => ({ ...f, [champ]: e.target.value }));
    setPage(0);
  };
  const notifier = (message, severity = 'success') => setToast({ open: true, message, severity });

  const retablir = async (s) => {
    try {
      await sanctionsService.retablir(s.id);
      notifier('Levée annulée : la sanction est de nouveau en cours.');
      charger();
    } catch (e) {
      notifier(getApiErrorMessage(e, 'Opération impossible.'), 'error');
    }
  };

  const supprimer = async () => {
    try {
      await sanctionsService.remove(suppression.id);
      notifier('Sanction supprimée.');
      setSuppression(null);
      charger();
    } catch (e) {
      notifier(getApiErrorMessage(e, 'Suppression impossible.'), 'error');
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, justifyContent: 'space-between', alignItems: { xs: 'stretch', sm: 'center' }, gap: 2, mb: 3 }}>
        <Box>
          <Typography variant="h5" fontWeight="bold" color="primary" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <GavelIcon /> Discipline
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Avertissements, blâmes et exclusions des étudiants.
          </Typography>
        </Box>
        {peutAgir && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => setFormulaire({ open: true, sanction: null })}>
            Nouvelle sanction
          </Button>
        )}
      </Box>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={6} md={3}><Chiffre titre="Sanctions en cours" valeur={stats?.actives} couleur="error.main" /></Grid>
        <Grid item xs={6} md={3}><Chiffre titre="Étudiants concernés" valeur={stats?.etudiants_concernes} /></Grid>
        <Grid item xs={6} md={3}><Chiffre titre="Exclusions en cours" valeur={stats?.exclusions_en_cours} couleur="warning.main" /></Grid>
        <Grid item xs={6} md={3}><Chiffre titre="Sanctions levées" valeur={stats?.levees} couleur="success.main" /></Grid>
      </Grid>

      <Paper variant="outlined" sx={{ p: 2, mb: 2, borderRadius: 2 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              placeholder="Étudiant, matricule, classe ou motif…"
              value={filtres.q}
              onChange={changerFiltre('q')}
              fullWidth
              size="small"
              InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon fontSize="small" /></InputAdornment> }}
            />
          </Grid>
          <Grid item xs={6} md={3}>
            <TextField select label="Type" value={filtres.type} onChange={changerFiltre('type')} fullWidth size="small">
              <MenuItem value="">Tous</MenuItem>
              {TYPES_SANCTION.map((t) => <MenuItem key={t} value={t}>{t}</MenuItem>)}
            </TextField>
          </Grid>
          <Grid item xs={6} md={3}>
            <TextField select label="État" value={filtres.etat} onChange={changerFiltre('etat')} fullWidth size="small">
              <MenuItem value="">Tous</MenuItem>
              {Object.entries(ETATS).map(([v, e]) => <MenuItem key={v} value={v}>{e.label}</MenuItem>)}
            </TextField>
          </Grid>
        </Grid>
      </Paper>

      {erreur && <Alert severity="error" sx={{ mb: 2 }} action={<Button color="inherit" onClick={charger}>Réessayer</Button>}>{erreur}</Alert>}

      <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
        <Table size="small" sx={{ minWidth: 920 }}>
          <TableHead sx={{ bgcolor: '#F5F7FA' }}>
            <TableRow>
              <TableCell><strong>Date</strong></TableCell>
              <TableCell><strong>Étudiant</strong></TableCell>
              <TableCell><strong>Classe</strong></TableCell>
              <TableCell><strong>Sanction</strong></TableCell>
              <TableCell><strong>Motif</strong></TableCell>
              <TableCell><strong>Période</strong></TableCell>
              <TableCell align="center"><strong>État</strong></TableCell>
              <TableCell align="center"><strong>Actions</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {chargement ? (
              <TableRow><TableCell colSpan={8} align="center" sx={{ py: 4 }}><CircularProgress size={28} /></TableCell></TableRow>
            ) : visibles.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} sx={{ py: 4 }}>
                  <Typography variant="body2" color="text.secondary" align="center">
                    {sanctions.length ? 'Aucune sanction ne correspond aux filtres.' : 'Aucune sanction enregistrée.'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              visibles.map((s) => {
                const etat = ETATS[s.etat] || ETATS.active;
                const whatsapp = lienWhatsAppParent(s, config?.nom || 'SmartCampus');
                return (
                  <TableRow key={s.id} hover>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>{dateFr(s.date_sanction)}</TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>{s.etudiant_nom}</Typography>
                      <Typography variant="caption" color="text.secondary">{s.etudiant_matricule}</Typography>
                    </TableCell>
                    <TableCell>{s.classe_nom || '-'}</TableCell>
                    <TableCell>
                      <Chip size="small" label={s.type_sanction} color={COULEURS_TYPE[s.type_sanction] || 'default'}
                        variant={s.type_sanction === 'Exclusion définitive' ? 'filled' : 'outlined'} />
                    </TableCell>
                    <TableCell sx={{ maxWidth: 280 }}>
                      <Typography variant="body2">{s.motif}</Typography>
                      {s.etat === 'levee' && (
                        <Typography variant="caption" color="success.main" display="block">
                          Levée le {dateFr(s.date_levee)}{s.levee_par_nom ? ` par ${s.levee_par_nom}` : ''} : {s.motif_levee}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>{periodeSanction(s)}</TableCell>
                    <TableCell align="center">
                      <Chip size="small" label={etat.label} color={etat.color} variant={s.etat === 'active' ? 'filled' : 'outlined'} />
                    </TableCell>
                    <TableCell align="center" sx={{ whiteSpace: 'nowrap' }}>
                      {whatsapp && (
                        <Tooltip title={`Prévenir le parent sur WhatsApp${s.nom_parent ? ` (${s.nom_parent})` : ''}`}>
                          <IconButton size="small" component="a" href={whatsapp} target="_blank" rel="noopener noreferrer" sx={{ color: '#128C7E' }} aria-label="Prévenir le parent sur WhatsApp">
                            <WhatsAppIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {peutAgir && (
                        <>
                          <Tooltip title="Corriger">
                            <IconButton size="small" color="primary" onClick={() => setFormulaire({ open: true, sanction: s })} aria-label="Corriger la sanction">
                              <EditIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          {s.etat === 'levee' ? (
                            <Tooltip title="Annuler la levée">
                              <IconButton size="small" onClick={() => retablir(s)} aria-label="Annuler la levée">
                                <UndoIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          ) : (
                            <Tooltip title="Lever la sanction">
                              <IconButton size="small" color="success" onClick={() => setLevee(s)} aria-label="Lever la sanction">
                                <LockOpenIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                          <Tooltip title="Supprimer (erreur de saisie)">
                            <IconButton size="small" color="error" onClick={() => setSuppression(s)} aria-label="Supprimer la sanction">
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={filtrees.length}
        page={page}
        onPageChange={(e, p) => setPage(p)}
        rowsPerPage={parPage}
        onRowsPerPageChange={(e) => { setParPage(parseInt(e.target.value, 10)); setPage(0); }}
        rowsPerPageOptions={[20, 50, 100]}
        labelRowsPerPage="Lignes"
      />

      <SanctionFormDialog
        open={formulaire.open}
        sanction={formulaire.sanction}
        etudiants={etudiants}
        onClose={() => setFormulaire({ open: false, sanction: null })}
        onSaved={(res, edition) => {
          setFormulaire({ open: false, sanction: null });
          notifier(edition ? 'Sanction corrigée.' : `Sanction enregistrée pour ${res?.etudiant_nom || "l'étudiant"}.`);
          charger();
        }}
      />
      <LeverSanctionDialog
        open={Boolean(levee)}
        sanction={levee}
        onClose={() => setLevee(null)}
        onDone={() => {
          setLevee(null);
          notifier('Sanction levée.');
          charger();
        }}
      />
      <Dialog open={Boolean(suppression)} onClose={() => setSuppression(null)} maxWidth="xs" fullWidth>
        <DialogTitle>Supprimer la sanction ?</DialogTitle>
        <DialogContent>
          <Typography variant="body2">
            {suppression?.type_sanction} du {dateFr(suppression?.date_sanction)} pour <strong>{suppression?.etudiant_nom}</strong>.
          </Typography>
          <Alert severity="warning" sx={{ mt: 2 }}>
            La suppression efface la sanction de l&apos;historique : réservez-la aux erreurs de saisie. Pour une sanction
            purgée ou pardonnée, utilisez plutôt « Lever la sanction ».
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSuppression(null)}>Annuler</Button>
          <Button color="error" variant="contained" onClick={supprimer}>Supprimer</Button>
        </DialogActions>
      </Dialog>
      <Snackbar open={toast.open} autoHideDuration={4000} onClose={() => setToast((t) => ({ ...t, open: false }))}>
        <Alert severity={toast.severity} onClose={() => setToast((t) => ({ ...t, open: false }))}>{toast.message}</Alert>
      </Snackbar>
    </Box>
  );
}
