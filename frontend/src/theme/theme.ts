'use client';

import { createTheme, responsiveFontSizes } from '@mui/material/styles';
import { Inter } from 'next/font/google';

const inter = Inter({ subsets: ['latin'] });

export const createAppTheme = (config: any = {}) => {
  const primaryColor = config?.couleur_primaire || '#193A7F';
  const secondaryColor = config?.couleur_secondaire || '#FF9800'; 
  const textColor = config?.couleur_texte || '#333333';
  const fontFamily = config?.typographie || inter.style.fontFamily;

  const theme = createTheme({
    typography: {
      fontFamily: fontFamily,
      button: {
        textTransform: 'none',
        fontWeight: 500,
      },
    },
    palette: {
      mode: 'light',
      primary: {
        main: primaryColor,
      },
      secondary: {
        main: secondaryColor,
      },
      background: {
        default: '#F5F7FA',
        paper: '#FFFFFF',
      },
      text: {
        primary: textColor,
        secondary: '#666666',
      },
    },
    shape: {
      borderRadius: 8,
    },
    components: {
      MuiButton: {
        styleOverrides: {
          root: {
            borderRadius: 8,
            padding: '8px 16px',
            '@media (max-width:599.95px)': {
              padding: '6px 12px',
            },
          },
          containedPrimary: {
            boxShadow: 'none',
            '&:hover': {
              boxShadow: `0px 4px 10px ${primaryColor}40`,
            },
          },
        },
      },
      // ---- Responsive : réglages communs à toutes les pages ----
      MuiTabs: {
        // Les barres d'onglets défilent horizontalement au lieu de déborder sur mobile.
        defaultProps: {
          variant: 'scrollable',
          scrollButtons: 'auto',
          allowScrollButtonsMobile: true,
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            '@media (max-width:599.95px)': {
              minWidth: 0,
              paddingLeft: 12,
              paddingRight: 12,
            },
          },
        },
      },
      MuiDialog: {
        styleOverrides: {
          paper: {
            // Sur téléphone : la fenêtre occupe presque tout l'écran (marges de 12 px).
            '@media (max-width:599.95px)': {
              '&:not(.MuiDialog-paperFullScreen)': {
                margin: 12,
                width: 'calc(100% - 24px)',
                maxWidth: 'calc(100% - 24px)',
                maxHeight: 'calc(100% - 24px)',
              },
            },
          },
        },
      },
      MuiDialogTitle: {
        styleOverrides: {
          root: {
            '@media (max-width:599.95px)': {
              padding: '14px 16px',
              fontSize: '1.05rem',
            },
          },
        },
      },
      MuiDialogContent: {
        styleOverrides: {
          root: {
            '@media (max-width:599.95px)': {
              padding: '12px 16px',
            },
          },
        },
      },
      MuiDialogActions: {
        styleOverrides: {
          root: {
            flexWrap: 'wrap',
            gap: 8,
            '& > :not(style) ~ :not(style)': { marginLeft: 0 },
            '@media (max-width:599.95px)': {
              padding: '10px 16px 14px',
            },
          },
        },
      },
      MuiTableContainer: {
        styleOverrides: {
          root: {
            overflowX: 'auto',
            WebkitOverflowScrolling: 'touch',
          },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          root: {
            '@media (max-width:599.95px)': {
              padding: '8px 10px',
              fontSize: '0.8125rem',
            },
          },
        },
      },
      MuiCardContent: {
        styleOverrides: {
          root: {
            '@media (max-width:599.95px)': {
              padding: 14,
              '&:last-child': { paddingBottom: 14 },
            },
          },
        },
      },
      MuiToolbar: {
        styleOverrides: {
          root: {
            flexWrap: 'wrap',
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            boxShadow: '0px 4px 20px rgba(0, 0, 0, 0.05)',
            borderRadius: 12,
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          elevation1: {
            boxShadow: '0px 4px 20px rgba(0, 0, 0, 0.05)',
          },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            borderRadius: 8,
          },
        },
      },
      MuiMenu: {
        styleOverrides: {
          paper: {
            maxHeight: 340,
            overflowY: 'auto',
            borderRadius: 8,
            boxShadow: '0px 8px 24px rgba(0, 0, 0, 0.12)',
            '& .MuiList-root': {
              maxHeight: 340,
              overflowY: 'auto',
            },
          },
        },
      },
      MuiSelect: {
        defaultProps: {
          MenuProps: {
            PaperProps: {
              style: {
                maxHeight: 340,
                overflowY: 'auto',
              },
            },
          },
        },
      },
      MuiAutocomplete: {
        styleOverrides: {
          paper: {
            maxHeight: 340,
            overflowY: 'auto',
          },
          listbox: {
            maxHeight: 340,
            overflowY: 'auto',
          },
        },
      },
      MuiPopover: {
        styleOverrides: {
          paper: {
            maxHeight: 340,
          },
        },
      },
    },
  });

  // Titres (h1 à h6) automatiquement réduits sur les petits écrans.
  return responsiveFontSizes(theme);
};

export const theme = createAppTheme();
