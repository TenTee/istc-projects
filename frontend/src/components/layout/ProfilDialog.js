'use client';

/**
 * « Mon profil » (menu du compte, en haut à droite) : disponible pour le personnel,
 * les étudiants et les formateurs. Chacun y change son nom d'utilisateur et son mot
 * de passe ; le mot de passe actuel est toujours demandé.
 */
import React from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  InputAdornment,
  Stack,
  TextField,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import PersonIcon from '@mui/icons-material/Person';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import { monCompteService } from '../../services/api/services';
import { getApiErrorMessage } from '../../services/api/client';

function premiereErreur(valeur) {
  if (!valeur) return '';
  return Array.isArray(valeur) ? valeur.join(' ') : String(valeur);
}

function erreursDeChamps(error) {
  const data = error?.response?.data;
  return data && typeof data === 'object' && !Array.isArray(data) ? data : {};
}

function ChampMotDePasse({ label, value, onChange, error, helperText, autoComplete }) {
  const [visible, setVisible] = React.useState(false);
  return (
    <TextField
      label={label}
      type={visible ? 'text' : 'password'}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      error={Boolean(error)}
      helperText={error || helperText}
      autoComplete={autoComplete}
      fullWidth
      size="small"
      InputProps={{
        endAdornment: (
          <InputAdornment position="end">
            <IconButton
              onClick={() => setVisible((v) => !v)}
              edge="end"
              size="small"
              aria-label={visible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
            >
              {visible ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
            </IconButton>
          </InputAdornment>
        ),
      }}
    />
  );
}

function majUtilisateurLocal(username) {
  try {
    const brut = localStorage.getItem('user');
    if (!brut) return;
    const u = JSON.parse(brut);
    localStorage.setItem('user', JSON.stringify({ ...u, username }));
  } catch {
    /* stockage indisponible */
  }
}

const VIDE_MDP = { actuel: '', nouveau: '', confirmation: '' };

export default function ProfilDialog({ open, onClose }) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const [compte, setCompte] = React.useState(null);
  const [chargement, setChargement] = React.useState(false);
  const [erreurChargement, setErreurChargement] = React.useState('');

  const [username, setUsername] = React.useState('');
  const [mdpPourNom, setMdpPourNom] = React.useState('');
  const [erreursNom, setErreursNom] = React.useState({});
  const [okNom, setOkNom] = React.useState('');
  const [envoiNom, setEnvoiNom] = React.useState(false);

  const [mdp, setMdp] = React.useState(VIDE_MDP);
  const [erreursMdp, setErreursMdp] = React.useState({});
  const [okMdp, setOkMdp] = React.useState('');
  const [envoiMdp, setEnvoiMdp] = React.useState(false);

  React.useEffect(() => {
    if (!open) return undefined;
    let actif = true;
    const timer = setTimeout(() => {
      setChargement(true);
      setErreurChargement('');
      setOkNom('');
      setOkMdp('');
      setErreursNom({});
      setErreursMdp({});
      setMdpPourNom('');
      setMdp(VIDE_MDP);
      monCompteService
        .get()
        .then((data) => {
          if (!actif || !data) return;
          setCompte(data);
          setUsername(data.username || '');
        })
        .catch((e) => actif && setErreurChargement(getApiErrorMessage(e, 'Impossible de charger votre profil.')))
        .finally(() => actif && setChargement(false));
    }, 0);
    return () => {
      actif = false;
      clearTimeout(timer);
    };
  }, [open]);

  const changerNom = async (e) => {
    e.preventDefault();
    setOkNom('');
    setErreursNom({});
    if (!username.trim() || username.trim() === compte?.username) {
      setErreursNom({ username: "Saisissez un nom d'utilisateur différent de l'actuel." });
      return;
    }
    if (!mdpPourNom) {
      setErreursNom({ mot_de_passe_actuel: 'Saisissez votre mot de passe actuel.' });
      return;
    }
    setEnvoiNom(true);
    try {
      const data = await monCompteService.changerNomUtilisateur(username.trim(), mdpPourNom);
      setCompte(data);
      setUsername(data.username);
      setMdpPourNom('');
      majUtilisateurLocal(data.username);
      setOkNom(`Nom d'utilisateur modifié : connectez-vous désormais avec « ${data.username} ».`);
    } catch (err) {
      const champs = erreursDeChamps(err);
      setErreursNom({
        username: premiereErreur(champs.username),
        mot_de_passe_actuel: premiereErreur(champs.mot_de_passe_actuel),
        general: champs.username || champs.mot_de_passe_actuel ? '' : getApiErrorMessage(err),
      });
    } finally {
      setEnvoiNom(false);
    }
  };

  const changerMotDePasse = async (e) => {
    e.preventDefault();
    setOkMdp('');
    const locales = {};
    if (!mdp.actuel) locales.mot_de_passe_actuel = 'Saisissez votre mot de passe actuel.';
    if (!mdp.nouveau) locales.nouveau_mot_de_passe = 'Saisissez le nouveau mot de passe.';
    if (mdp.nouveau && mdp.confirmation !== mdp.nouveau) locales.confirmation = 'Les deux saisies sont différentes.';
    setErreursMdp(locales);
    if (Object.keys(locales).length) return;
    setEnvoiMdp(true);
    try {
      await monCompteService.changerMotDePasse({
        mot_de_passe_actuel: mdp.actuel,
        nouveau_mot_de_passe: mdp.nouveau,
        confirmation: mdp.confirmation,
      });
      setMdp(VIDE_MDP);
      setOkMdp('Mot de passe modifié. Utilisez-le à votre prochaine connexion.');
    } catch (err) {
      const champs = erreursDeChamps(err);
      const connu = champs.mot_de_passe_actuel || champs.nouveau_mot_de_passe || champs.confirmation;
      setErreursMdp({
        mot_de_passe_actuel: premiereErreur(champs.mot_de_passe_actuel),
        nouveau_mot_de_passe: premiereErreur(champs.nouveau_mot_de_passe),
        confirmation: premiereErreur(champs.confirmation),
        general: connu ? '' : getApiErrorMessage(err),
      });
    } finally {
      setEnvoiMdp(false);
    }
  };

  const nomComplet = compte ? [compte.noms, compte.prenoms].filter(Boolean).join(' ') : '';

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth fullScreen={fullScreen} scroll="paper">
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <PersonIcon color="primary" />
        Mon profil
      </DialogTitle>
      <DialogContent dividers>
        {chargement && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        )}
        {erreurChargement && <Alert severity="error">{erreurChargement}</Alert>}
        {compte && !chargement && (
          <>
            <Box sx={{ mb: 2 }}>
              {nomComplet && (
                <Typography variant="subtitle1" fontWeight="bold">
                  {nomComplet}
                </Typography>
              )}
              <Typography variant="body2" color="text.secondary" sx={{ overflowWrap: 'break-word' }}>
                {[compte.role_libelle || compte.role, compte.email].filter(Boolean).join(' · ')}
              </Typography>
            </Box>

            <Divider sx={{ mb: 2 }} />
            <Box component="form" onSubmit={changerNom} noValidate>
              <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
                Nom d&apos;utilisateur
              </Typography>
              <Stack spacing={1.5}>
                {okNom && <Alert severity="success">{okNom}</Alert>}
                {erreursNom.general && <Alert severity="error">{erreursNom.general}</Alert>}
                <TextField
                  label="Nom d'utilisateur"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  error={Boolean(erreursNom.username)}
                  helperText={erreursNom.username || 'Lettres sans accent, chiffres et . @ + - _ (pas d’espace).'}
                  autoComplete="username"
                  fullWidth
                  size="small"
                />
                <ChampMotDePasse
                  label="Mot de passe actuel"
                  value={mdpPourNom}
                  onChange={setMdpPourNom}
                  error={erreursNom.mot_de_passe_actuel}
                  autoComplete="current-password"
                />
                <Box>
                  <Button type="submit" variant="outlined" disabled={envoiNom}>
                    {envoiNom ? 'Enregistrement…' : "Changer le nom d'utilisateur"}
                  </Button>
                </Box>
              </Stack>
            </Box>

            <Divider sx={{ my: 2.5 }} />
            <Box component="form" onSubmit={changerMotDePasse} noValidate>
              <Typography variant="subtitle2" sx={{ mb: 1.5 }}>
                Mot de passe
              </Typography>
              <Stack spacing={1.5}>
                {okMdp && <Alert severity="success">{okMdp}</Alert>}
                {erreursMdp.general && <Alert severity="error">{erreursMdp.general}</Alert>}
                <ChampMotDePasse
                  label="Mot de passe actuel"
                  value={mdp.actuel}
                  onChange={(v) => setMdp((m) => ({ ...m, actuel: v }))}
                  error={erreursMdp.mot_de_passe_actuel}
                  autoComplete="current-password"
                />
                <ChampMotDePasse
                  label="Nouveau mot de passe"
                  value={mdp.nouveau}
                  onChange={(v) => setMdp((m) => ({ ...m, nouveau: v }))}
                  error={erreursMdp.nouveau_mot_de_passe}
                  helperText="Au moins 8 caractères, pas uniquement des chiffres, ni trop proche de votre nom."
                  autoComplete="new-password"
                />
                <ChampMotDePasse
                  label="Confirmer le nouveau mot de passe"
                  value={mdp.confirmation}
                  onChange={(v) => setMdp((m) => ({ ...m, confirmation: v }))}
                  error={erreursMdp.confirmation}
                  autoComplete="new-password"
                />
                <Box>
                  <Button type="submit" variant="contained" disabled={envoiMdp}>
                    {envoiMdp ? 'Enregistrement…' : 'Changer le mot de passe'}
                  </Button>
                </Box>
              </Stack>
            </Box>
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Fermer</Button>
      </DialogActions>
    </Dialog>
  );
}
