'use client';

/**
 * Numéro de version en bas des menus latéraux + fenêtre « Nouveautés ».
 * Les données viennent de config/versions.json, mis à jour automatiquement
 * à chaque livraison (outils/version/versionner.py, GitHub Action « Version »).
 */
import React from 'react';
import {
  Box,
  ButtonBase,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Button,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from '@mui/material';
import NewReleasesOutlinedIcon from '@mui/icons-material/NewReleasesOutlined';
import historique from '../../config/versions.json';

const VERSIONS = historique.versions || [];
export const VERSION_ACTUELLE = VERSIONS[0]?.version || '0.0.0';
const CLE_VUE = 'smartcampus_version_vue';
const LIBELLES_NIVEAU = { majeure: 'Version majeure', mineure: 'Nouvelles fonctions', correctif: 'Corrections' };

function formaterDate(iso) {
  if (!iso) return '';
  const [a, m, j] = iso.split('-');
  return `${j}/${m}/${a}`;
}

export default function VersionInfo({ compact = false }) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down('sm'));
  const [ouvert, setOuvert] = React.useState(false);
  const [nonVue, setNonVue] = React.useState(false);

  // Pastille « nouveau » tant que l'utilisateur n'a pas ouvert les nouveautés de cette version.
  React.useEffect(() => {
    let vue = null;
    try {
      vue = localStorage.getItem(CLE_VUE);
    } catch {
      /* navigation privée */
    }
    const timer = setTimeout(() => setNonVue(vue !== VERSION_ACTUELLE), 0);
    return () => clearTimeout(timer);
  }, []);

  const ouvrir = () => {
    setOuvert(true);
    setNonVue(false);
    try {
      localStorage.setItem(CLE_VUE, VERSION_ACTUELLE);
    } catch {
      /* navigation privée */
    }
  };

  const date = formaterDate(VERSIONS[0]?.date);
  const pastille = nonVue && (
    <Box
      component="span"
      aria-label="Nouveautés non lues"
      sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: '#FFB74D', flexShrink: 0 }}
    />
  );

  return (
    <>
      <Tooltip title={compact ? `Version ${VERSION_ACTUELLE} · Nouveautés` : 'Voir les nouveautés'} placement="right" arrow>
        <ButtonBase
          onClick={ouvrir}
          aria-label={`Version ${VERSION_ACTUELLE}, voir les nouveautés`}
          sx={{
            width: '100%',
            mt: 0.5,
            px: compact ? 0.5 : 2,
            py: 0.75,
            borderRadius: 2,
            display: 'flex',
            alignItems: 'center',
            justifyContent: compact ? 'center' : 'flex-start',
            gap: 1,
            color: 'rgba(255,255,255,0.6)',
            fontSize: '0.72rem',
            lineHeight: 1.3,
            textAlign: 'left',
            '&:hover': { color: 'rgba(255,255,255,0.9)', backgroundColor: 'rgba(255,255,255,0.08)' },
          }}
        >
          {compact ? (
            <>
              <span>v{VERSION_ACTUELLE}</span>
              {pastille}
            </>
          ) : (
            <>
              <NewReleasesOutlinedIcon sx={{ fontSize: 16, flexShrink: 0 }} />
              <Box component="span" sx={{ minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                Version {VERSION_ACTUELLE}
                {date ? ` · ${date}` : ''}
              </Box>
              {pastille}
            </>
          )}
        </ButtonBase>
      </Tooltip>

      <Dialog open={ouvert} onClose={() => setOuvert(false)} maxWidth="sm" fullWidth fullScreen={fullScreen} scroll="paper">
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <NewReleasesOutlinedIcon color="primary" />
          Nouveautés de SmartCampus
        </DialogTitle>
        <DialogContent dividers>
          {VERSIONS.map((v, index) => (
            <Box key={v.version} sx={{ mb: index === VERSIONS.length - 1 ? 0 : 3 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                <Typography variant="subtitle1" fontWeight="bold">
                  Version {v.version}
                </Typography>
                {index === 0 && <Chip size="small" color="primary" label="Version actuelle" />}
                {v.niveau && <Chip size="small" variant="outlined" label={LIBELLES_NIVEAU[v.niveau] || v.niveau} />}
                <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
                  {formaterDate(v.date)}
                </Typography>
              </Box>
              <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
                {(v.changements || []).map((c) => (
                  <Typography component="li" variant="body2" key={c} sx={{ mb: 0.5 }}>
                    {c}
                  </Typography>
                ))}
              </Box>
            </Box>
          ))}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOuvert(false)} variant="contained">
            Fermer
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
