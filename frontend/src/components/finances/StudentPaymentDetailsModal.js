import React, { useEffect, useState } from 'react';
import {
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
  Paper,
  Snackbar,
  Alert,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import AddCardIcon from '@mui/icons-material/AddCard';
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import PersonIcon from '@mui/icons-material/Person';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import PrintIcon from '@mui/icons-material/Print';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import HistoryIcon from '@mui/icons-material/History';
import DescriptionIcon from '@mui/icons-material/Description';

import { paiementsService, studentScheduleService } from '@/services/api/services';
import { getMediaUrl } from '@/services/api/client';
import { formatDate } from '@/utils/formatters';
import { obtenirPdf } from '@/utils/documentsPdf';
import { useUserPermissions } from '@/utils/permissions';
import CorrectionPaiementDialog, { MOYENS_PAIEMENT } from './CorrectionPaiementDialog';

const LIBELLES_MOYENS = Object.fromEntries(MOYENS_PAIEMENT.map((m) => [m.value, m.label]));
const LIBELLES_ACTIONS = { creation: 'Création', modification: 'Correction', suppression: 'Suppression' };

function resumeJournal(entree) {
  const avant = entree.avant || {};
  const apres = entree.apres || {};
  if (entree.action === 'suppression') return `${formatFCFA(avant.montant_paye)} supprimé`;
  if (entree.action === 'creation') return formatFCFA(apres.montant_paye);
  const changements = [];
  if (avant.montant_paye !== apres.montant_paye) changements.push(`${formatFCFA(avant.montant_paye)} → ${formatFCFA(apres.montant_paye)}`);
  if (avant.paiement_type !== apres.paiement_type) changements.push(`type : ${avant.paiement_type} → ${apres.paiement_type}`);
  if (avant.moyen_paiement !== apres.moyen_paiement) {
    changements.push(`mode : ${LIBELLES_MOYENS[avant.moyen_paiement] || avant.moyen_paiement || '-'} → ${LIBELLES_MOYENS[apres.moyen_paiement] || apres.moyen_paiement}`);
  }
  if (avant.date_paiement !== apres.date_paiement) {
    changements.push(`date : ${new Date(avant.date_paiement).toLocaleDateString('fr-FR')} → ${new Date(apres.date_paiement).toLocaleDateString('fr-FR')}`);
  }
  return changements.join(' ; ') || 'Aucun changement de valeur';
}

function formatFCFA(val) {
  return `${Number(val || 0).toLocaleString('fr-FR')} FCFA`;
}

export default function StudentPaymentDetailsModal({
  open,
  onClose,
  student,
  onOpenPayment,
  onChanged,
}) {
  const { canWrite } = useUserPermissions();
  const peutCorriger = canWrite('can_manage_finance');
  const [journal, setJournal] = useState([]);
  const [correction, setCorrection] = useState({ open: false, mode: 'modifier', paiement: null });
  const [message, setMessage] = useState({ open: false, texte: '', severite: 'success' });
  const [pdfEnCours, setPdfEnCours] = useState('');

  const ouvrirPdf = async (cle, url, mode, nomParDefaut) => {
    setPdfEnCours(cle);
    try {
      await obtenirPdf(url, { mode, nomParDefaut });
    } catch (e) {
      setMessage({ open: true, texte: e.message, severite: 'error' });
    } finally {
      setPdfEnCours('');
    }
  };
  const [currentTab, setCurrentTab] = useState(0);
  const [payments, setPayments] = useState([]);
  const [scheduleData, setScheduleData] = useState(null);
  const [loadingPayments, setLoadingPayments] = useState(true);
  const [loadingSchedule, setLoadingSchedule] = useState(true);
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));

  useEffect(() => {
    if (open && student?.etudiant) {
      fetchStudentDetails(student.etudiant);
    }
  }, [open, student]);

  const fetchStudentDetails = async (etudiantId) => {
    setLoadingPayments(true);
    setLoadingSchedule(true);
    try {
      const [paymentsRes, scheduleRes, journalRes] = await Promise.all([
        paiementsService.list({ etudiant: etudiantId }).catch(() => []),
        studentScheduleService.get(etudiantId).catch(() => null),
        paiementsService.journal({ etudiant: etudiantId }).catch(() => []),
      ]);
      setPayments(Array.isArray(paymentsRes) ? paymentsRes : paymentsRes?.results || []);
      setScheduleData(scheduleRes);
      setJournal(Array.isArray(journalRes) ? journalRes : journalRes?.results || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingPayments(false);
      setLoadingSchedule(false);
    }
  };

  if (!student) return null;

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md" fullScreen={fullScreen}>
      <DialogTitle sx={{ fontWeight: 700, color: 'primary.main', display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' }, gap: 1.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <PersonIcon color="primary" />
          <span>Fiche Financière & Historique des Paiements</span>
        </Box>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        <Button
          variant="outlined"
          size="small"
          startIcon={<DescriptionIcon />}
          disabled={pdfEnCours === 'facture'}
          onClick={() =>
            ouvrirPdf('facture', paiementsService.urlFacture(student.etudiant), 'telecharger', 'facture.pdf')
          }
        >
          {pdfEnCours === 'facture' ? 'Génération…' : 'Facture PDF'}
        </Button>
        {onOpenPayment && (Number(student.solde_restant) || 0) > 0 && (
          <Button
            variant="contained"
            color="success"
            size="small"
            startIcon={<AddCardIcon />}
            onClick={() => {
              onClose();
              onOpenPayment(student);
            }}
          >
            Enregistrer un paiement
          </Button>
        )}
        </Box>
      </DialogTitle>
      <DialogContent dividers>
        {/* Banner Étudiant & Synthèse */}
        <Paper variant="outlined" sx={{ p: 2, mb: 3, borderRadius: 2, bgcolor: '#f8fafc' }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={6}>
              <Typography variant="caption" color="text.secondary" fontWeight={700}>ÉTUDIANT & FORMATION</Typography>
              <Typography variant="h6" fontWeight={700} color="primary.dark">
                {student.etudiant_nom}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Class / Formation: <strong>{student.formation_nom}</strong>
              </Typography>
              {student.type_reduction && student.type_reduction !== 'NONE' && (
                <Box sx={{ mt: 1 }}>
                  <Chip
                    label={
                      student.type_reduction === 'BOURSE'
                        ? `Bourse ${student.bourse_code ? `(${student.bourse_code})` : ''} -${formatFCFA(student.montant_reduction)}`
                        : student.type_reduction === 'PERCENT_10'
                        ? `Réduction 10% (-${formatFCFA(student.montant_reduction)})`
                        : `Réduction libre (-${formatFCFA(student.montant_reduction)})`
                    }
                    color="secondary"
                    size="small"
                    sx={{ fontWeight: 700 }}
                  />
                </Box>
              )}
            </Grid>

            <Grid item xs={12} md={6}>
              <Grid container spacing={1}>
                <Grid item xs={4}>
                  <Card variant="outlined" sx={{ bgcolor: '#fff', textCenter: 'center', p: 1 }}>
                    <Typography variant="caption" color="text.secondary">TOTAL DÛ</Typography>
                    <Typography variant="body2" fontWeight={700} sx={{ overflowWrap: 'anywhere' }}>{formatFCFA(student.montant_du)}</Typography>
                  </Card>
                </Grid>
                <Grid item xs={4}>
                  <Card variant="outlined" sx={{ bgcolor: '#f0fdf4', textCenter: 'center', p: 1, borderColor: '#bbf7d0' }}>
                    <Typography variant="caption" color="success.main">PAYÉ</Typography>
                    <Typography variant="body2" fontWeight={700} color="success.main" sx={{ overflowWrap: 'anywhere' }}>{formatFCFA(student.montant_paye_total)}</Typography>
                  </Card>
                </Grid>
                <Grid item xs={4}>
                  <Card variant="outlined" sx={{ bgcolor: '#fef2f2', textCenter: 'center', p: 1, borderColor: '#fecaca' }}>
                    <Typography variant="caption" color="error.main">SOLDE</Typography>
                    <Typography variant="body2" fontWeight={700} color="error.main" sx={{ overflowWrap: 'anywhere' }}>{formatFCFA(student.solde_restant)}</Typography>
                  </Card>
                </Grid>
              </Grid>
            </Grid>
          </Grid>
        </Paper>

        <Tabs value={currentTab} onChange={(e, v) => setCurrentTab(v)} sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Tab icon={<ReceiptLongIcon fontSize="small" />} iconPosition="start" label={`Historique & Reçus (${payments.length})`} />
          <Tab icon={<CalendarMonthIcon fontSize="small" />} iconPosition="start" label="Échéancier des Tranches" />
          <Tab icon={<HistoryIcon fontSize="small" />} iconPosition="start" label={`Journal (${journal.length})`} />
        </Tabs>

        {/* TAB 0: HISTORIQUE DES PAIEMENTS & JUSTIFICATIFS */}
        {currentTab === 0 && (
          <Box>
            {loadingPayments ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress size={28} />
              </Box>
            ) : payments.length > 0 ? (
              <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
                <Table size="small" sx={{ minWidth: 860 }}>
                  <TableHead sx={{ bgcolor: '#f1f5f9' }}>
                    <TableRow>
                      <TableCell><strong>N° de reçu</strong></TableCell>
                      <TableCell><strong>Date & Heure</strong></TableCell>
                      <TableCell><strong>Type</strong></TableCell>
                      <TableCell><strong>Montant Payé</strong></TableCell>
                      <TableCell><strong>Mode</strong></TableCell>
                      <TableCell align="center"><strong>Justificatif</strong></TableCell>
                      <TableCell align="center"><strong>Reçu & actions</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {payments.map((p) => (
                      <TableRow key={p.id} hover>
                        <TableCell sx={{ whiteSpace: 'nowrap', fontFamily: 'monospace' }}>{p.numero_recu || '-'}</TableCell>
                        <TableCell>{p.date_paiement ? new Date(p.date_paiement).toLocaleString('fr-FR') : '-'}</TableCell>
                        <TableCell>
                          <Chip
                            label={p.paiement_type === 'INSCRIPTION' ? "Frais d'inscription" : "Frais de formation"}
                            color={p.paiement_type === 'INSCRIPTION' ? 'info' : 'primary'}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell sx={{ fontWeight: 700, color: 'success.main' }}>
                          {formatFCFA(p.montant_paye)}
                        </TableCell>
                        <TableCell>{LIBELLES_MOYENS[p.moyen_paiement] || p.moyen_paiement || 'Espèces'}</TableCell>
                        <TableCell align="center" sx={{ whiteSpace: 'nowrap' }}>
                          {p.justificatif ? (
                            <Button
                              variant="outlined"
                              color="primary"
                              size="small"
                              startIcon={<AttachFileIcon />}
                              endIcon={<OpenInNewIcon fontSize="small" />}
                              component="a"
                              href={getMediaUrl(p.justificatif)}
                              target="_blank"
                              rel="noopener noreferrer"
                              sx={{ textTransform: 'none', py: 0.2 }}
                            >
                              Voir le justificatif
                            </Button>
                          ) : (
                            <Chip label="Aucun" size="small" variant="outlined" color="default" />
                          )}
                        </TableCell>
                        <TableCell align="center" sx={{ whiteSpace: 'nowrap' }}>
                          <Tooltip title="Télécharger le reçu (PDF)">
                            <span>
                              <IconButton
                                size="small"
                                color="primary"
                                disabled={pdfEnCours === `recu-${p.id}`}
                                onClick={() => ouvrirPdf(`recu-${p.id}`, paiementsService.urlRecu(p.id), 'telecharger', `recu-${p.numero_recu || p.id}.pdf`)}
                                aria-label="Télécharger le reçu"
                              >
                                <PictureAsPdfIcon fontSize="small" />
                              </IconButton>
                            </span>
                          </Tooltip>
                          <Tooltip title="Ouvrir le reçu pour l'imprimer">
                            <IconButton
                              size="small"
                              onClick={() => ouvrirPdf(`imp-${p.id}`, paiementsService.urlRecu(p.id), 'ouvrir')}
                              aria-label="Imprimer le reçu"
                            >
                              <PrintIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          {peutCorriger && (
                            <>
                              <Tooltip title="Corriger le paiement">
                                <IconButton
                                  size="small"
                                  color="warning"
                                  onClick={() => setCorrection({ open: true, mode: 'modifier', paiement: { ...p, etudiant_nom: p.etudiant_nom || student.etudiant_nom } })}
                                  aria-label="Corriger le paiement"
                                >
                                  <EditIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                              <Tooltip title="Supprimer le paiement">
                                <IconButton
                                  size="small"
                                  color="error"
                                  onClick={() => setCorrection({ open: true, mode: 'supprimer', paiement: { ...p, etudiant_nom: p.etudiant_nom || student.etudiant_nom } })}
                                  aria-label="Supprimer le paiement"
                                >
                                  <DeleteIcon fontSize="small" />
                                </IconButton>
                              </Tooltip>
                            </>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 3 }}>
                Aucun paiement n&apos;a été effectué pour cet étudiant.
              </Typography>
            )}
          </Box>
        )}

        {/* TAB 1: ÉCHÉANCIER DE REGLEMENT */}
        {currentTab === 1 && (
          <Box>
            {loadingSchedule ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress size={28} />
              </Box>
            ) : scheduleData?.installments?.length > 0 ? (
              <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
                <Table size="small" sx={{ minWidth: 750 }}>
                  <TableHead sx={{ bgcolor: '#f1f5f9' }}>
                    <TableRow>
                      <TableCell><strong>Ordre</strong></TableCell>
                      <TableCell><strong>Tranche / Libellé</strong></TableCell>
                      <TableCell><strong>Date Échéance</strong></TableCell>
                      <TableCell><strong>Montant Dû</strong></TableCell>
                      <TableCell><strong>Montant Payé</strong></TableCell>
                      <TableCell><strong>Reste à Payer</strong></TableCell>
                      <TableCell><strong>Statut</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {scheduleData.installments.map((inst, idx) => (
                      <TableRow key={idx} hover>
                        <TableCell>{inst.order}</TableCell>
                        <TableCell sx={{ fontWeight: 600 }}>{inst.label}</TableCell>
                        <TableCell>{formatDate(inst.due_date)}</TableCell>
                        <TableCell>{formatFCFA(inst.amount_due)}</TableCell>
                        <TableCell sx={{ color: 'success.main', fontWeight: 600 }}>{formatFCFA(inst.amount_paid)}</TableCell>
                        <TableCell sx={{ color: Number(inst.balance_due) > 0 ? 'error.main' : 'text.secondary', fontWeight: 700 }}>
                          {formatFCFA(inst.balance_due)}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={
                              inst.status === 'PAID'
                                ? 'Payée'
                                : inst.status === 'PARTIAL'
                                ? 'Partielle'
                                : inst.status === 'OVERDUE'
                                ? 'En retard'
                                : 'En attente'
                            }
                            color={
                              inst.status === 'PAID'
                                ? 'success'
                                : inst.status === 'PARTIAL'
                                ? 'warning'
                                : inst.status === 'OVERDUE'
                                ? 'error'
                                : 'default'
                            }
                            size="small"
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 3 }}>
                Aucun échéancier configuré pour cette classe ou cet étudiant.
              </Typography>
            )}
          </Box>
        )}

        {/* TAB 2: JOURNAL DES PAIEMENTS (création, correction, suppression) */}
        {currentTab === 2 && (
          <Box>
            {journal.length > 0 ? (
              <TableContainer component={Paper} variant="outlined" sx={{ borderRadius: 2 }}>
                <Table size="small" sx={{ minWidth: 760 }}>
                  <TableHead sx={{ bgcolor: '#f1f5f9' }}>
                    <TableRow>
                      <TableCell><strong>Date</strong></TableCell>
                      <TableCell><strong>Opération</strong></TableCell>
                      <TableCell><strong>N° de reçu</strong></TableCell>
                      <TableCell><strong>Détail</strong></TableCell>
                      <TableCell><strong>Motif</strong></TableCell>
                      <TableCell><strong>Par</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {journal.map((j) => (
                      <TableRow key={j.id} hover>
                        <TableCell sx={{ whiteSpace: 'nowrap' }}>{new Date(j.date).toLocaleString('fr-FR')}</TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            label={LIBELLES_ACTIONS[j.action] || j.action}
                            color={j.action === 'suppression' ? 'error' : j.action === 'modification' ? 'warning' : 'default'}
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell sx={{ fontFamily: 'monospace', whiteSpace: 'nowrap' }}>{j.numero_recu || '-'}</TableCell>
                        <TableCell>{resumeJournal(j)}</TableCell>
                        <TableCell>{j.motif || '-'}</TableCell>
                        <TableCell>{j.utilisateur_nom || '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Typography variant="body2" color="text.secondary" align="center" sx={{ py: 3 }}>
                Aucune opération enregistrée dans le journal pour cet étudiant.
              </Typography>
            )}
          </Box>
        )}
      </DialogContent>
      <CorrectionPaiementDialog
        open={correction.open}
        mode={correction.mode}
        paiement={correction.paiement}
        onClose={() => setCorrection((c) => ({ ...c, open: false }))}
        onDone={(texte) => {
          setCorrection((c) => ({ ...c, open: false }));
          setMessage({ open: true, texte, severite: 'success' });
          fetchStudentDetails(student.etudiant);
          onChanged?.();
        }}
      />
      <Snackbar
        open={message.open}
        autoHideDuration={5000}
        onClose={() => setMessage((m) => ({ ...m, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity={message.severite} onClose={() => setMessage((m) => ({ ...m, open: false }))}>
          {message.texte}
        </Alert>
      </Snackbar>
      <DialogActions sx={{ p: 2 }}>
        <Button onClick={onClose} variant="contained" color="primary">
          Fermer
        </Button>
      </DialogActions>
    </Dialog>
  );
}
