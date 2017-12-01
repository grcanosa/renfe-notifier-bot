#!/usr/bin/python3



texts = {

"WELCOME": "Hola, soy tu avisador personal de billetes de Renfe.",
"NOT_AUTH_REPLY": "Hola, {username}, por ahora no estás autorizado a usar este servicio. "
                    "Solicitando acceso a admin.",
"ADMIN_USER_REQ_ACCESS": "Usuario {username} solicita acceso",
"OPTION_SELECTION": "Hola, qué quieres hacer hoy?",
"MAIN_OP_ADD_QUERY" : "Añadir consulta periódica",
"MAIN_OP_DEL_QUERY" : "Eliminar consulta periódica",
"MAIN_OP_DO_QUERY" : "Hacer consulta ahora",
"MAIN_OP_UNKNOWN": "Lo siento, no te he entendido. ",
"DO_ONETIME_QUERY": "Ok, voy a hacer una consulta puntual.",
"ADD_PERIODIC_QUERY": "Ok, voy a añadir una consulta periódica.",
"SELECT_ORIGIN_STATION": "Introduce estación de origen.",
"SELECT_DESTINATION_STATION": "Introduce estación de destino.",
"SELECT_TRIP_DATE": "Elige ahora la fecha del viaje.",
"SELECTED_TRIP": "Has seleccionado el trayecto {origin}->{destination}",
"SELECTED_DATA": "Perfecto, has seleccionado el trayecto {origin}->{destination}"
                    " para el día {date}",
"FOUND_N_TRAINS": "He encontrado {ntrains} trenes con asientos disponibles para"
                    " el trayecto {origin}->{destination} para el día {date}",
"NO_TRAINS_FOUND": "No hay trenes para el trayecto {origin}->{destination} para el día {date}",
"TRAIN_INFO": "De {t_departure} a {t_arrival}, €: {cost}, T: {ticket_type}"
}


keyboards = {
"MAIN_OPTIONS": [[texts["MAIN_OP_DO_QUERY"]],
                [texts["MAIN_OP_ADD_QUERY"]],
                [texts["MAIN_OP_DEL_QUERY"]]
                ]
,
"STATIONS" : [["MADRID-PUERTA DE ATOCHA",
                "SEVILLA-SANTA JUSTA"],
                ["BARCELONA-SANTS",
                "VALENCIA"],
                ["ALICANTE",
                "MALAGA"]
            ]
}
