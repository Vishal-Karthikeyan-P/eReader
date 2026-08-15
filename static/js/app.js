let books = [];

let currentFilter = "all";

let isListView = false;


/* --------------------------------
   INITIALIZATION
-------------------------------- */

document.addEventListener("DOMContentLoaded", async () => {

    const folder =
        localStorage.getItem("driveFolder");

    /*
     * No folder configured
     */
    if (!folder) {

        window.location.href = "/setup";

        return;
    }


    /*
     * Show cached books immediately
     */
    const cached =
        localStorage.getItem("library");

    if (cached) {

        try {

            books = JSON.parse(cached);

            renderBooks();
            renderContinueReading();
            renderHistory();

        } catch (error) {

            console.error(error);

        }

    }


    /*
     * Always check Drive when
     * bookshelf is opened.
     */

    await checkForUpdates(false);

});


/* --------------------------------
   CHECK DRIVE
-------------------------------- */

async function checkForUpdates(showMessage = true) {

    const folder =
        localStorage.getItem("driveFolder");

    if (!folder) {

        window.location.href = "/setup";

        return;
    }


    const status =
        document.getElementById("libraryStatus");

    if (showMessage) {

        status.innerText =
            "Checking Google Drive...";
    }


    try {

        const response =
            await fetch(
                "/api/library?folder=" +
                encodeURIComponent(folder)
            );


        const data =
            await response.json();


        if (!data.success) {

            status.innerText =
                "Unable to update library.";

            return;
        }


        const oldBooks =
            JSON.stringify(books);

        const newBooks =
            JSON.stringify(data.books);


        books =
            data.books;


        /*
         * Store the generated books.json
         * locally in the browser.
         */

        localStorage.setItem(
            "library",
            JSON.stringify(books)
        );


        localStorage.setItem(
            "libraryLastChecked",
            Date.now().toString()
        );


        renderBooks();
        renderContinueReading();
        renderHistory();


        if (oldBooks !== newBooks) {

            status.innerText =
                `${books.length} books • Library updated`;

        } else {

            status.innerText =
                `${books.length} books • Up to date`;
        }


    } catch (error) {

        console.error(error);

        status.innerText =
            "Unable to check Google Drive.";

    }

}


/* --------------------------------
   BOOK CARD
-------------------------------- */

function createBookCard(book) {

    const progress =
        getProgress(book.id);

    const completed =
        isCompleted(book.id);


    const card =
        document.createElement("div");

    card.className =
        "book-card";


    let cover = "";

    if (book.thumbnail) {

        cover = `
            <img
                src="${book.thumbnail}"
                class="book-cover"
                alt="">
        `;

    } else {

        cover = `
            <div class="book-cover-placeholder">
                ${book.type.toUpperCase()}
            </div>
        `;

    }


    card.innerHTML = `

        <div class="cover-container">

            ${cover}

            <span class="book-type">
                ${book.type.toUpperCase()}
            </span>

        </div>


        <div class="book-info">

            <h3>
                ${escapeHtml(book.title)}
            </h3>


            <div class="progress-container">

                <div
                    class="progress-bar"
                    style="width:${progress}%">
                </div>

            </div>


            <div class="book-meta">

                <span>
                    ${progress}% read
                </span>

                ${
                    completed
                    ? `<span class="completed">
                         ✓ Completed
                       </span>`
                    : ""
                }

            </div>


            <button
                class="read-button">

                ${
                    completed
                    ? "Read Again"
                    : progress > 0
                    ? "Continue Reading"
                    : "Start Reading"
                }

            </button>

        </div>

    `;


    card.querySelector(".read-button")
        .addEventListener(
            "click",
            () => openBook(book)
        );


    return card;
}


/* --------------------------------
   RENDER BOOKS
-------------------------------- */

function renderBooks() {

    const container =
        document.getElementById("books");

    container.innerHTML = "";


    let filtered =
        books.filter(book => {

            const progress =
                getProgress(book.id);

            const completed =
                isCompleted(book.id);


            if (currentFilter === "completed") {

                return completed;

            }


            if (currentFilter === "progress") {

                return progress > 0 && !completed;

            }


            return true;

        });


    if (filtered.length === 0) {

        container.innerHTML = `
            <div class="empty-state">
                <div>📚</div>
                <h3>No books found</h3>
                <p>
                    Add PDF or EPUB files to your
                    Google Drive folder.
                </p>
            </div>
        `;

        return;
    }


    filtered.forEach(book => {

        container.appendChild(
            createBookCard(book)
        );

    });

}


/* --------------------------------
   CONTINUE READING
-------------------------------- */

function renderContinueReading() {

    const section =
        document.getElementById(
            "continueSection"
        );

    const container =
        document.getElementById(
            "continueBooks"
        );


    container.innerHTML = "";


    const reading =
        books
        .filter(book => {

            const progress =
                getProgress(book.id);

            return progress > 0 &&
                   progress < 100 &&
                   !isCompleted(book.id);

        })
        .sort(
            (a, b) =>
                getLastRead(b.id) -
                getLastRead(a.id)
        )
        .slice(0, 4);


    if (reading.length === 0) {

        section.style.display = "none";

        return;
    }


    section.style.display = "block";


    reading.forEach(book => {

        container.appendChild(
            createBookCard(book)
        );

    });

}


/* --------------------------------
   HISTORY
-------------------------------- */

function renderHistory() {

    const container =
        document.getElementById("history");


    const history =
        JSON.parse(
            localStorage.getItem(
                "readingHistory"
            ) || "[]"
        );


    container.innerHTML = "";


    if (history.length === 0) {

        container.innerHTML =
            "<p>No reading history yet.</p>";

        return;
    }


    history
        .slice(0, 10)
        .forEach(item => {

            const book =
                books.find(
                    b => b.id === item.bookId
                );


            if (!book) {
                return;
            }


            const div =
                document.createElement("div");

            div.className =
                "history-item";


            div.innerHTML = `

                <div>

                    <strong>
                        ${escapeHtml(book.title)}
                    </strong>

                    <small>
                        ${new Date(
                            item.timestamp
                        ).toLocaleString()}
                    </small>

                </div>

                <button>
                    Continue
                </button>
            `;


            div.querySelector("button")
                .onclick =
                () => openBook(book);


            container.appendChild(div);

        });

}


/* --------------------------------
   OPEN BOOK
-------------------------------- */

function openBook(book) {

    localStorage.setItem(
        "lastOpenedBook",
        book.id
    );


    const history =
        JSON.parse(
            localStorage.getItem(
                "readingHistory"
            ) || "[]"
        );


    const filtered =
        history.filter(
            item => item.bookId !== book.id
        );


    filtered.unshift({
        bookId: book.id,
        timestamp: Date.now()
    });


    localStorage.setItem(
        "readingHistory",
        JSON.stringify(filtered.slice(0, 50))
    );


    window.location.href =
        "/reader?id=" +
        encodeURIComponent(book.id);
}


/* --------------------------------
   PROGRESS
-------------------------------- */

function getProgress(id) {

    return Number(
        localStorage.getItem(
            `progress_${id}`
        ) || 0
    );

}


function setProgress(id, progress) {

    progress =
        Math.max(
            0,
            Math.min(
                100,
                Math.round(progress)
            )
        );


    localStorage.setItem(
        `progress_${id}`,
        progress
    );


    if (progress >= 100) {

        localStorage.setItem(
            `completed_${id}`,
            "true"
        );

    }


}


function isCompleted(id) {

    return localStorage.getItem(
        `completed_${id}`
    ) === "true";

}


function getLastRead(id) {

    return Number(
        localStorage.getItem(
            `lastRead_${id}`
        ) || 0
    );

}


/* --------------------------------
   FILTERS
-------------------------------- */

document
.querySelectorAll(".filter-button")
.forEach(button => {

    button.addEventListener(
        "click",
        () => {

            document
            .querySelectorAll(
                ".filter-button"
            )
            .forEach(
                b => b.classList.remove("active")
            );


            button.classList.add("active");


            currentFilter =
                button.dataset.filter;


            renderBooks();

        }
    );

});


/* --------------------------------
   REFRESH
-------------------------------- */

document
.getElementById("refreshButton")
.addEventListener(
    "click",
    () => checkForUpdates(true)
);


/* --------------------------------
   CHANGE FOLDER
-------------------------------- */

document
.getElementById("changeFolderButton")
.addEventListener(
    "click",
    () => {

        localStorage.removeItem(
            "driveFolder"
        );

        window.location.href =
            "/setup";

    }
);


/* --------------------------------
   VIEW
-------------------------------- */

document
.getElementById("viewButton")
.addEventListener(
    "click",
    () => {

        isListView =
            !isListView;


        const booksContainer =
            document.getElementById("books");


        if (isListView) {

            booksContainer.classList.add(
                "list-view"
            );

        } else {

            booksContainer.classList.remove(
                "list-view"
            );

        }

    }
);


/* --------------------------------
   HTML ESCAPE
-------------------------------- */

function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent =
        text;

    return div.innerHTML;

}
