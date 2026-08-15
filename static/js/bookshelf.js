const STORAGE_KEY =
    "ereader_library_v1";


/* =====================================================
   STORAGE
===================================================== */

function getLibrary() {

    try {

        return JSON.parse(
            localStorage.getItem(
                STORAGE_KEY
            ) || "{}"
        );

    } catch {

        return {};

    }

}


function getBookId(card) {

    return (
        card.dataset.title
        + "|"
        + card.dataset.url
    );

}


/* =====================================================
   UPDATE CARDS
===================================================== */

function updateCards() {

    const library =
        getLibrary();


    document
        .querySelectorAll(".book-card")
        .forEach(card => {

            const id =
                getBookId(card);


            const data =
                library[id];


            if (!data) {

                return;

            }


            const progress =
                Math.max(
                    0,
                    Math.min(
                        100,
                        Number(
                            data.progress
                        ) || 0
                    )
                );


            const percentage =
                card.querySelector(
                    ".percentage"
                );


            const status =
                card.querySelector(
                    ".status-text"
                );


            const progressBar =
                card.querySelector(
                    ".progress-fill"
                );


            const completedBadge =
                card.querySelector(
                    ".completed-badge"
                );


            const readLabel =
                card.querySelector(
                    ".read-label"
                );


            percentage.textContent =
                progress + "%";


            progressBar.style.width =
                progress + "%";


            if (
                data.completed
                || progress >= 100
            ) {

                status.textContent =
                    "Completed";

                completedBadge.hidden =
                    false;

                readLabel.textContent =
                    "Read Again";

            }

            else if (progress > 0) {

                status.textContent =
                    "Continue Reading";

                completedBadge.hidden =
                    true;

                readLabel.textContent =
                    "Continue Reading";

            }

            else {

                status.textContent =
                    "Not started";

                completedBadge.hidden =
                    true;

                readLabel.textContent =
                    "Read Book";

            }

        });

}


/* =====================================================
   FILTERS
===================================================== */

let currentFilter =
    "all";


function applyFilter() {

    const library =
        getLibrary();


    document
        .querySelectorAll(".book-card")
        .forEach(card => {

            const id =
                getBookId(card);


            const data =
                library[id];


            const progress =
                data
                    ? Number(data.progress) || 0
                    : 0;


            const completed =
                data
                    ? data.completed
                    : false;


            let visible = true;


            if (
                currentFilter ===
                "continue"
            ) {

                visible =
                    progress > 0
                    && progress < 100
                    && !completed;

            }


            if (
                currentFilter ===
                "completed"
            ) {

                visible =
                    completed
                    || progress >= 100;

            }


            if (
                currentFilter ===
                "history"
            ) {

                visible =
                    Boolean(
                        data
                    );

            }


            card.style.display =
                visible
                    ? ""
                    : "none";

        });

}


document
    .querySelectorAll(".filter")
    .forEach(button => {

        button.addEventListener(
            "click",
            () => {

                document
                    .querySelectorAll(
                        ".filter"
                    )
                    .forEach(
                        item =>
                            item.classList
                                .remove(
                                    "active"
                                )
                    );


                button.classList.add(
                    "active"
                );


                currentFilter =
                    button.dataset.filter;


                applyFilter();

            }
        );

    });


/* =====================================================
   GRID / LIST
===================================================== */

const booksGrid =
    document.getElementById(
        "booksGrid"
    );


const gridButton =
    document.getElementById(
        "gridButton"
    );


const listButton =
    document.getElementById(
        "listButton"
    );


const VIEW_KEY =
    "ereader_view";


function setView(view) {

    if (view === "list") {

        booksGrid.classList.add(
            "list-view"
        );

        listButton.classList.add(
            "active"
        );

        gridButton.classList.remove(
            "active"
        );

    } else {

        booksGrid.classList.remove(
            "list-view"
        );

        gridButton.classList.add(
            "active"
        );

        listButton.classList.remove(
            "active"
        );

    }


    localStorage.setItem(
        VIEW_KEY,
        view
    );

}


gridButton.addEventListener(
    "click",
    () => setView("grid")
);


listButton.addEventListener(
    "click",
    () => setView("list")
);


const savedView =
    localStorage.getItem(
        VIEW_KEY
    );


if (savedView) {

    setView(savedView);

}


/* =====================================================
   INITIALIZE
===================================================== */

updateCards();

applyFilter();