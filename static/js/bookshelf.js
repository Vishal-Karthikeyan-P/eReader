const STORAGE_KEY =
    "ereader_library_v1";

const FOLDER_KEY =
    "driveFolderUrl";

const VIEW_KEY =
    "ereader_view";


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
   LOAD BOOKS FROM GOOGLE DRIVE
===================================================== */

async function loadBooks() {

    const folderUrl =
        localStorage.getItem(
            FOLDER_KEY
        );


    /*
       No Drive folder has been saved.
       Send the user to setup.
    */

    if (!folderUrl) {

        window.location.href =
            "/setup";

        return;

    }


    try {

        console.log(
            "Loading books from:",
            folderUrl
        );


        const response =
            await fetch(
                "/api/books?folder="
                + encodeURIComponent(
                    folderUrl
                )
            );


        /*
           Read the response as text first.
           This prevents the vague:
           JSON.parse unexpected character
           error.
        */

        const responseText =
            await response.text();


        console.log(
            "Books API response:",
            responseText
        );


        let data;


        try {

            data =
                JSON.parse(
                    responseText
                );

        } catch (error) {

            console.error(
                "Invalid JSON returned by /api/books:",
                responseText
            );

            throw new Error(
                "Server returned invalid JSON."
            );

        }


        if (
            !response.ok
            || !data.success
        ) {

            throw new Error(
                data.error
                || "Unable to load books."
            );

        }


        const books =
            data.books || [];


        console.log(
            "Books found:",
            books.length
        );


        renderBooks(
            books
        );


        updateCards();

        applyFilter();


    } catch (error) {

        console.error(
            "Failed to load books:",
            error
        );


        showBooksError(
            error.message
        );

    }

}


/* =====================================================
   RENDER BOOKS
===================================================== */

function renderBooks(books) {

    const container =
        document.getElementById(
            "booksGrid"
        );


    if (!container) {

        console.error(
            "booksGrid element not found."
        );

        return;

    }


    container.innerHTML = "";


    if (!books.length) {

        container.innerHTML = `

            <div class="no-books">

                <h2>No books found</h2>

                <p>
                    No PDF or EPUB books were found
                    in your Google Drive folder.
                </p>

                <button
                    onclick="checkForUpdates()"
                >
                    Check Again
                </button>

            </div>

        `;

        return;

    }


    books.forEach(
        book => {

            const card =
                createBookCard(
                    book
                );


            container.appendChild(
                card
            );

        }
    );

}


/* =====================================================
   CREATE BOOK CARD
===================================================== */

function createBookCard(book) {

    const card =
        document.createElement(
            "div"
        );


    card.className =
        "book-card";


    /*
       Use title + link as the same
       identity system your existing
       progress code uses.
    */

    card.dataset.title =
        book.title || book.name;


    card.dataset.url =
        book.download_url
        || book.link
        || "";


    const library =
        getLibrary();


    const id =
        getBookId(card);


    const saved =
        library[id]
        || {};


    const progress =
        Math.max(
            0,
            Math.min(
                100,
                Number(
                    saved.progress
                ) || 0
            )
        );


    const completed =
        saved.completed
        || progress >= 100;


    const cover =
        book.thumbnail
        || "";


    const title =
        escapeHTML(
            book.title
            || book.name
            || "Untitled"
        );


    const type =
        (
            book.type
            || ""
        ).toUpperCase();


    card.innerHTML = `

        <div class="book-cover">

            ${
                cover
                ?
                `
                <img
                    src="${cover}"
                    alt="${title}"
                    loading="lazy"
                >
                `
                :
                `
                <div class="cover-placeholder">
                    📚
                </div>
                `
            }

            <span class="book-type">
                ${type}
            </span>

            <span
                class="completed-badge"
                ${completed ? "" : "hidden"}
            >
                ✓ Completed
            </span>

        </div>


        <div class="book-info">

            <h3 class="book-title">
                ${title}
            </h3>


            <div class="progress-container">

                <div class="progress-bar">

                    <div
                        class="progress-fill"
                        style="width:${progress}%"
                    ></div>

                </div>


                <span class="percentage">
                    ${progress}%
                </span>

            </div>


            <div class="status-text">

                ${
                    completed
                    ? "Completed"
                    : progress > 0
                    ? "Continue Reading"
                    : "Not started"
                }

            </div>


            <button
                class="read-button"
                type="button"
            >

                <span class="read-label">

                    ${
                        completed
                        ? "Read Again"
                        : progress > 0
                        ? "Continue Reading"
                        : "Read Book"
                    }

                </span>

            </button>

        </div>

    `;


    /*
       Open reader
    */

    const readButton =
        card.querySelector(
            ".read-button"
        );


    readButton.addEventListener(
        "click",
        () => {

            /*
               Store the complete book object.
               The reader can use download_url.
            */

            localStorage.setItem(
                "currentBook",
                JSON.stringify(
                    book
                )
            );


            /*
               Also store the book ID separately.
            */

            localStorage.setItem(
                "currentBookId",
                book.id
            );


            /*
               Reader determines PDF/EPUB
               from this object.
            */

            window.location.href =
                "/reader";

        }
    );


    return card;

}


/* =====================================================
   HTML ESCAPE
===================================================== */

function escapeHTML(value) {

    return String(
        value || ""
    )
        .replace(
            /&/g,
            "&amp;"
        )
        .replace(
            /</g,
            "&lt;"
        )
        .replace(
            />/g,
            "&gt;"
        )
        .replace(
            /"/g,
            "&quot;"
        )
        .replace(
            /'/g,
            "&#039;"
        );

}


/* =====================================================
   UPDATE CARDS
===================================================== */

function updateCards() {

    const library =
        getLibrary();


    document
        .querySelectorAll(
            ".book-card"
        )
        .forEach(
            card => {

                const id =
                    getBookId(
                        card
                    );


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


                if (percentage) {

                    percentage.textContent =
                        progress + "%";

                }


                if (progressBar) {

                    progressBar.style.width =
                        progress + "%";

                }


                if (
                    data.completed
                    || progress >= 100
                ) {

                    if (status) {

                        status.textContent =
                            "Completed";

                    }


                    if (completedBadge) {

                        completedBadge.hidden =
                            false;

                    }


                    if (readLabel) {

                        readLabel.textContent =
                            "Read Again";

                    }

                }

                else if (
                    progress > 0
                ) {

                    if (status) {

                        status.textContent =
                            "Continue Reading";

                    }


                    if (completedBadge) {

                        completedBadge.hidden =
                            true;

                    }


                    if (readLabel) {

                        readLabel.textContent =
                            "Continue Reading";

                    }

                }

                else {

                    if (status) {

                        status.textContent =
                            "Not started";

                    }


                    if (completedBadge) {

                        completedBadge.hidden =
                            true;

                    }


                    if (readLabel) {

                        readLabel.textContent =
                            "Read Book";

                    }

                }

            }
        );

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
        .querySelectorAll(
            ".book-card"
        )
        .forEach(
            card => {

                const id =
                    getBookId(
                        card
                    );


                const data =
                    library[id];


                const progress =
                    data
                    ? Number(
                        data.progress
                    ) || 0
                    : 0;


                const completed =
                    data
                    ? data.completed
                    : false;


                let visible =
                    true;


                if (
                    currentFilter ===
                    "continue"
                ) {

                    visible =
                        progress > 0
                        &&
                        progress < 100
                        &&
                        !completed;

                }


                if (
                    currentFilter ===
                    "completed"
                ) {

                    visible =
                        completed
                        ||
                        progress >= 100;

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

            }
        );

}


/* =====================================================
   FILTER BUTTONS
===================================================== */

document
    .querySelectorAll(
        ".filter"
    )
    .forEach(
        button => {

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

        }
    );


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


function setView(view) {

    if (!booksGrid) {

        return;

    }


    if (
        view === "list"
    ) {

        booksGrid.classList.add(
            "list-view"
        );


        if (listButton) {

            listButton.classList.add(
                "active"
            );

        }


        if (gridButton) {

            gridButton.classList.remove(
                "active"
            );

        }

    }

    else {

        booksGrid.classList.remove(
            "list-view"
        );


        if (gridButton) {

            gridButton.classList.add(
                "active"
            );

        }


        if (listButton) {

            listButton.classList.remove(
                "active"
            );

        }

    }


    localStorage.setItem(
        VIEW_KEY,
        view
    );

}


if (gridButton) {

    gridButton.addEventListener(
        "click",
        () => setView("grid")
    );

}


if (listButton) {

    listButton.addEventListener(
        "click",
        () => setView("list")
    );

}


const savedView =
    localStorage.getItem(
        VIEW_KEY
    );


if (savedView) {

    setView(
        savedView
    );

}


/* =====================================================
   MANUAL UPDATE
===================================================== */

async function checkForUpdates() {

    const button =
        document.getElementById(
            "checkUpdatesButton"
        );


    if (button) {

        button.disabled =
            true;

        button.textContent =
            "Checking...";

    }


    await loadBooks();


    if (button) {

        button.disabled =
            false;

        button.textContent =
            "Check for Updates";

    }

}


/* =====================================================
   ERROR DISPLAY
===================================================== */

function showBooksError(
    message
) {

    const container =
        document.getElementById(
            "booksGrid"
        );


    if (!container) {

        return;

    }


    container.innerHTML = `

        <div class="books-error">

            <h2>
                Unable to load books
            </h2>

            <p>
                ${escapeHTML(message)}
            </p>

            <button
                type="button"
                onclick="checkForUpdates()"
            >
                Try Again
            </button>

        </div>

    `;

}


/* =====================================================
   INITIALIZE
===================================================== */

loadBooks();
