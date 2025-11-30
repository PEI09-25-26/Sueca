#include <stdlib.h>
#include <stdio.h>
#include <time.h>
#include <ctype.h>
// As cartas do baralho de sueca têm duas características:  valor (2,3,4,5,6,Q,J,K,7,A)
//                                                          naipe (C, D, H, S)
// Podemos codificar as cartas usando números inteiros de 0 a 39:
// 00 01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39
// C2 C3 C4 C5 C6 CQ CJ CK C7 CA D2 D3 D4 D5 D6 DQ DJ DK D7 DA H2 H3 H4 H5 H6 HQ HJ HK H7 HA S2 S3 S4 S5 S6 SQ SJ SK S7 SA
// Os naipes com inteiros de 0 a 3:         e os valores com inteiros de 0 a 9:
// 0 1 2 3                                  // 0 1 2 3 4 5 6 7 8 9
// C D H S                                  // 2 3 4 5 6 Q J K 7 A
// Assim, o naipe de uma carta é dado pela divisão inteira do código da carta pelo tamanho de um naipe (SUITSIZE)
// e o valor dessa mesma carta será o resto dessa divisão inteira  

// Variáveis globais (estrutura de dados) e constantes auxiliares
#define NSUITS 4
#define SUITSIZE 10
char suit_icon[]={'C', 'D', 'H', 'S'};
char rank_icon[]={'2', '3', '4', '5', '6', 'Q', 'J', 'K', '7', 'A'};
short points[]={0,0,0,0,0,2,3,4,10,11,
                0,0,0,0,0,2,3,4,10,11,
                0,0,0,0,0,2,3,4,10,11,
                0,0,0,0,0,2,3,4,10,11};
#define DECKSIZE 40 // NSUITS*SUITSIZE

typedef short card;
#define NPLAYERS 4
const char *Plr_name[]={"North", "West", "South", "East"};
enum Player {North, West, South, East}; // Na sueca joga-se no sentido directo
#define NTRICKS 10
card  hands[NPLAYERS][NTRICKS];
card tricks[NTRICKS][NPLAYERS];
short lead_player[NTRICKS]; // registo auxiliar associado a 'tricks'
card trump; // o trunfo é exibido na mesa

// protótipos de funções
int random_number(int);
card * open_deck(void);
void close_deck(card *);
void shuffle(card *, int, int);
void cut(card *, int);
card deal(card *, short);
short suit (card);
short rank (card);
void show(card *, short, short);
void advance(short *);
card play(short, short);
void sort_hand(card *);
int compare_sh(const void *p1, const void *p2);

int main(void) {
    card *deck=open_deck(); // Abrir o baralho
    card played, top;
    int game=1; char go_on='S';
    short turn, dealer, winner, first_turn=North; // O primeiro a baralhar é Norte;
    short trick_score, total_score[2]; // 0 - NS; 1 - EW

    srand(time(NULL));
    do { // um jogo
        turn=first_turn; dealer=(turn+3)%NPLAYERS;
        printf("É %s a baralhar\n", Plr_name[turn]);            shuffle(deck, 15, 10);
        printf("É %s a partir\n", Plr_name[(turn+2)%NPLAYERS]); cut(deck, 15);
        printf("É %s a dar\n", Plr_name[dealer]);         trump=deal(deck, dealer);
        sort_hand(&(hands[North][0])); sort_hand(&(hands[West][0]));
        sort_hand(&(hands[South][0])); sort_hand(&(hands[East][0]));
        printf("Prema qualquer tecla para começar o jogo..\n"); getchar();
        total_score[0]=0; total_score[1]=0; // incialização da pontuação do jogo
        for (int t=0; t<NTRICKS; t++) {                 // jogo=NTRICKS vazas
            printf("Trunfo:\n"); show(&trump, 1, 0);
            show(&hands[North][0], NTRICKS-t, 35); show(&hands[West] [0], NTRICKS-t, 15);
            show(&hands[East] [0], NTRICKS-t, 55); show(&hands[South][0], NTRICKS-t, 35);
            for (int i=0; i<t; i++) {
                show(&tricks[i][0], NPLAYERS, 10);
            }
            printf("vaza %d\n", t+1);
            winner=turn;            // inicialização da vaza
            lead_player[t]=winner;  // inicialização da vaza
            trick_score=0;          // inicialização da vaza
            for (int i=0; i<NPLAYERS; i++) {            // vaza=NPLAYERS cartas
                // printf("%s: \n", Plr_name[turn]); debug
                played=play(turn, t); // o jogador que tem a vez ('turn') joga a vaza 't'
                trick_score+=points[played];
                if (i==0) // a primeira carta da vaza assume sempre a posição de 'top'
                    { top=played; winner=turn; }
                else { // o 'top' pode ser destronado por:
                    if (suit(played)==suit(top) ) {      // uma carta do mesmo naipe
                        if (rank(played)>rank(top))      // que seja de maior valor
                            { top=played; winner=turn; }
                    }
                    else                                 // uma carta de outro naipe
                        if (suit(played)==suit(trump))   // se esse naipe for trunfo
                            { top=played; winner=turn; } 
                }
                advance(&turn);
            }
            show(&tricks[t][North], 1, 35); show(&tricks[t][West], 1, 15);
            show(&tricks[t][East], 1, 55); show(&tricks[t][South], 1, 35);
            total_score[winner%2]+=trick_score; // acumula pontos da vaza para o par vencedor
            turn=winner; // vez passa para quem venceu a vaza;
            printf("Qualquer tecla para avançar para a próxima vaza\n"); getchar(); system("clear");
        }
        printf("Resultado do jogo %d: NS- %d   EW- %d\n", game+1, total_score[0], total_score[1]);
        game++; advance(&first_turn); printf("Novo jogo? (S/N)"); scanf(" %c", &go_on);
    } while (toupper(go_on)=='S');

    close_deck(deck); // 'Arrumar' o baralho
    return EXIT_SUCCESS;
}


int random_number(int N) {
    // gera um número inteiro aleatório entre 0 e N-1
    return (rand() % N);
}

card* open_deck(void) {
    // Reserva memória necessária, cria baralho em ordem canónica
    // ascendente e retorna ponteiro para o início desse baralho.
    card *d = (card *) malloc (DECKSIZE*sizeof(card));
    for (int i=0; i<DECKSIZE; i++) d[i]=i;
    return d;
}

void close_deck(card * deck) {
    // Liberta a memória reservada para o baralho dado.
    free (deck);
}

void shuffle(card *deck, int cut, int rep) {
    // Executa 'rep' acções de baralhar, em que o baralho é
    // dividido em partes de 'cut' e 'DECKSIZE-cut' cartas.
    if ( (cut>=DECKSIZE) || (cut<1) ) return; // força 0<cut<40
    card *d = (card *) malloc (DECKSIZE*sizeof(card));
    card *part1=d;      int N1=cut;
    card *part2=d+cut;  int N2=DECKSIZE-cut;
printf("A baralhar...\n");
    for (int r=0; r<rep; r++) {
        for (int i=0; i<DECKSIZE; i++) d[i]=deck[i]; // cria cópia
        int i=0, j=0;
        for (int m=0; m<DECKSIZE; m++) { // percorre o baralho a criar
            if (i==N1) // acabou a lista 1
                deck[m]=part2[j++];
            else
                if (j==N2) // acabou a lista 2
                    deck[m]=part1[i++];
                else // ainda há elementos em ambas
                    if ( 1+random_number(DECKSIZE-m)<=N1-i )
                        deck[m]=part1[i++];
                    else
                        deck[m]=part2[j++];
        }
//printf("...%da vez: \n", r+1); show(deck, DECKSIZE, 0);  // debug
    }
    free(d);
}

void cut(card * deck, int line) {
    // Parte o baralho por 'line' cartas.
printf("A partir...\n");
    if ( (line>=DECKSIZE) || (line<1) ) return; // força 0<line<40
    card deck_copy[DECKSIZE]; // VLA para cópia do baralho
    for (int i=0; i<DECKSIZE; i++) {
        deck_copy[i]=deck[i];
    }
    for (int i=0; i<DECKSIZE; i++)
        deck[i]=deck_copy[(i+line)%DECKSIZE];
}

card deal(card *deck, short dealer) {
    card t;
    if (random_number(2)) { 
        t=deck[0]; // tira trunfo por cima 
        for (int i=0; i<DECKSIZE; i++) // e dá pela esquerda
            hands[(dealer+NPLAYERS-i/NTRICKS)%NPLAYERS][i%NTRICKS]=deck[i];
    }
    else {
        t=deck[DECKSIZE-1]; // tira trunfo por baixo 
        for (int i=0; i<DECKSIZE; i++) // e dá pela direita
            hands[(dealer+1+i/NTRICKS)%NPLAYERS][i%NTRICKS]=deck[i];
    }
    return t;
}

short suit (card c) {
    return c/SUITSIZE;
}

short rank (card c) {
    return c%SUITSIZE;
}

void show(card *pt, short size, short spaces) {
    char indent[spaces+1];
    for (int i=0; i<spaces; i++) indent[i]=' '; indent[spaces]='\0'; 
    printf("%s", indent);
    for (int i=0; i<size; i++) {
        printf("%c", rank_icon[rank(pt[i])]);
        printf("%c", i==size-1 ? '\n' : ' ');
    }
    printf("%s", indent);
    for (int i=0; i<size; i++) {
        printf("%c", suit_icon[suit(pt[i])]);
        printf("%c", i==size-1 ? '\n' : ' '); 
    }
}

void advance(short *turn) {
    *turn=(*turn+1)%NPLAYERS;
}

card play(short turn, short trick) {
// Esta função decide e executa a jogada do jogador indicado por 'turn'
//                                          na vaza indicada por 'trick' 
// versão 0: joga completamente à sorte (nem sequer assiste!)
// retorna a carta jogada
    short card_index=random_number(NTRICKS-trick); // usa índice aleatório
    tricks[trick][turn]=hands[turn][card_index]; // para escolher a carta a jogar...
    for (int i=card_index; i<NTRICKS-trick-1; i++)
        hands[turn][i]=hands[turn][i+1]; // ... e retira-a da mão (cartas seguintes recuam)
    return tricks[trick][turn];
}

void sort_hand(card *hand) {
// Esta função ordena a mão apontada por 'hand', colocando as cartas por ordem descendente dentro do naipe,
// e os naipes por ordem decrescente de código. 
    qsort(hand, NTRICKS, sizeof(card), compare_sh);
}

int compare_sh(const void *p1, const void *p2) {
    short n1=*((int *)p1), n2=*((int *)p2);
    return n2-n1;
}