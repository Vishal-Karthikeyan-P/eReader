import * as pdfjsLib
    from "https://cdn.jsdelivr.net/npm/pdfjs-dist@6.1.200/build/pdf.min.mjs";


/* =====================================================
   CONFIG
===================================================== */

const config = window.READER_CONFIG;

const title = config.title;

const originalUrl = config.originalUrl;

const bookUrl = config.proxyUrl;


/* =====================================================
   PDF.JS WORKER
===================================================== */

pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdn.jsdelivr.net/npm/pdfjs-dist@6.1.200/build/pdf.worker.min.mjs";


/* =====================================================
   DOM
===================================================== */

const loadingScreen =
    document.getElementById("loadingScreen");

const errorScreen =
    document.getElementById("errorScreen");

const errorMessage =
    document.getElementById("errorMessage");

const pdfReader =
    document.getElementById("pdfReader");

const epubReader =
    document.getElementById("epubReader");

const readerType =
    document.getElementById("readerType");

const settingsPanel =
    document.getElementById("settingsPanel");


/* =====================================================
   STORAGE
===================================================== */

const STORAGE_KEY =
    "ereader_library_v1";


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


function saveLibrary(library) {

    localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify(library)
    );

}


function getBookId() {

    return (
        title
        + "|"
        + originalUrl
    );

}


function getBookData() {

    const library = getLibrary();

    const id = getBookId();

    if (!library[id]) {

        library[id] = {

            title: title,

            url: originalUrl,

            type: detectBookType(),

            progress: 0,

            completed: false,

            lastPage: 1,

            lastPosition: "",

            lastRead: Date.now(),

            created: Date.now()

        };

        saveLibrary(library);

    }

    return library[id];

}


function updateBookData(updates) {

    const library = getLibrary();

    const id = getBookId();

    if (!library[id]) {

        getBookData();

    }

    library[id] = {

        ...library[id],

        ...updates,

        lastRead: Date.now()

    };

    saveLibrary(library);

}


/* =====================================================
   BOOK TYPE
===================================================== */

function detectBookType() {

    const url = originalUrl.toLowerCase();

    if (
        url.includes(".epub")
        || url.includes("epub")
    ) {

        return "epub";

    }

    return "pdf";

}


/* =====================================================
   INITIALIZE
===================================================== */

async function initializeReader() {

    try {

        getBookData();

        restoreTheme();

        const type =
            detectBookType();

        if (type === "epub") {

            readerType.textContent =
                "EPUB";

            await loadEPUB();

        } else {

            readerType.textContent =
                "PDF";

            await loadPDF();

        }

        loadingScreen.classList.add(
            "hidden"
        );

    } catch (error) {

        console.error(error);

        showError(
            error.message
            || "Unable to open the book."
        );

    }

}


/* =====================================================
   ERROR
===================================================== */

function showError(message) {

    loadingScreen.classList.add(
        "hidden"
    );

    pdfReader.classList.add(
        "hidden"
    );

    epubReader.classList.add(
        "hidden"
    );

    errorMessage.textContent =
        message;

    errorScreen.classList.remove(
        "hidden"
    );

}


/* =====================================================
   PDF
===================================================== */

let pdfDocument = null;

let pdfCurrentPage = 1;

let pdfTotalPages = 0;

let pdfScale = 1;

let pdfRotation = 0;

let pdfRendering = false;


async function loadPDF() {

    pdfReader.classList.remove(
        "hidden"
    );


    const loadingTask =
        pdfjsLib.getDocument({

            url: bookUrl,

            rangeChunkSize:
                1024 * 1024

        });


    pdfDocument =
        await loadingTask.promise;


    pdfTotalPages =
        pdfDocument.numPages;


    document.getElementById(
        "pdfTotalPages"
    ).textContent =
        pdfTotalPages;


    const book =
        getBookData();


    pdfCurrentPage =
        Math.min(
            Math.max(
                Number(book.lastPage) || 1,
                1
            ),
            pdfTotalPages
        );


    await renderCurrentPDFPage();

    updatePDFProgress();

}


async function renderCurrentPDFPage() {

    if (!pdfDocument) {
        return;
    }


    if (pdfRendering) {
        return;
    }


    pdfRendering = true;


    try {

        const page =
            await pdfDocument.getPage(
                pdfCurrentPage
            );


        const viewport =
            page.getViewport({

                scale: pdfScale,

                rotation: pdfRotation

            });


        const outputScale =
            window.devicePixelRatio || 1;


        const container =
            document.getElementById(
                "pdfPages"
            );


        container.innerHTML = "";


        const pageElement =
            document.createElement(
                "div"
            );


        pageElement.className =
            "pdf-page";


        const canvas =
            document.createElement(
                "canvas"
            );


        const context =
            canvas.getContext(
                "2d"
            );


        canvas.width =
            Math.floor(
                viewport.width *
                outputScale
            );


        canvas.height =
            Math.floor(
                viewport.height *
                outputScale
            );


        canvas.style.width =
            Math.floor(
                viewport.width
            ) + "px";


        canvas.style.height =
            Math.floor(
                viewport.height
            ) + "px";


        pageElement.appendChild(
            canvas
        );


        const pageNumber =
            document.createElement(
                "div"
            );


        pageNumber.className =
            "pdf-page-number";


        pageNumber.textContent =
            `Page ${pdfCurrentPage}`;


        pageElement.appendChild(
            pageNumber
        );


        container.appendChild(
            pageElement
        );


        const renderContext = {

            canvasContext: context,

            viewport: viewport,

            transform:
                outputScale !== 1
                    ? [
                        outputScale,
                        0,
                        0,
                        outputScale,
                        0,
                        0
                    ]
                    : null

        };


        await page.render(
            renderContext
        ).promise;


        document.getElementById(
            "pdfPageInput"
        ).value =
            pdfCurrentPage;


        updatePDFProgress();


    } finally {

        pdfRendering = false;

    }

}


function updatePDFProgress() {

    if (!pdfTotalPages) {
        return;
    }


    const percentage =
        Math.round(
            (
                pdfCurrentPage
                / pdfTotalPages
            ) * 100
        );


    document.getElementById(
        "pdfProgress"
    ).textContent =
        percentage + "%";


    document.getElementById(
        "pdfProgressBar"
    ).style.width =
        percentage + "%";


    updateBookData({

        progress: percentage,

        lastPage: pdfCurrentPage,

        completed:
            percentage >= 100

    });

}


/* =====================================================
   PDF CONTROLS
===================================================== */

document
    .getElementById("pdfPrevious")
    .addEventListener(
        "click",
        async () => {

            if (
                pdfCurrentPage <= 1
            ) {

                return;

            }


            pdfCurrentPage--;

            await renderCurrentPDFPage();

        }
    );


document
    .getElementById("pdfNext")
    .addEventListener(
        "click",
        async () => {

            if (
                pdfCurrentPage >=
                pdfTotalPages
            ) {

                updateBookData({
                    completed: true,
                    progress: 100
                });

                return;

            }


            pdfCurrentPage++;

            await renderCurrentPDFPage();

        }
    );


document
    .getElementById("pdfPageInput")
    .addEventListener(
        "change",
        async event => {

            let page =
                Number(
                    event.target.value
                );


            if (
                !Number.isFinite(page)
            ) {

                page = 1;

            }


            page =
                Math.min(
                    Math.max(
                        page,
                        1
                    ),
                    pdfTotalPages
                );


            pdfCurrentPage =
                page;


            await renderCurrentPDFPage();

        }
    );


document
    .getElementById("pdfZoomIn")
    .addEventListener(
        "click",
        async () => {

            pdfScale =
                Math.min(
                    pdfScale + 0.1,
                    3
                );


            updateZoomLabel();

            await renderCurrentPDFPage();

        }
    );


document
    .getElementById("pdfZoomOut")
    .addEventListener(
        "click",
        async () => {

            pdfScale =
                Math.max(
                    pdfScale - 0.1,
                    0.5
                );


            updateZoomLabel();

            await renderCurrentPDFPage();

        }
    );


function updateZoomLabel() {

    document.getElementById(
        "pdfZoomValue"
    ).textContent =
        Math.round(
            pdfScale * 100
        ) + "%";

}


document
    .getElementById("pdfRotate")
    .addEventListener(
        "click",
        async () => {

            pdfRotation =
                (
                    pdfRotation
                    + 90
                ) % 360;


            await renderCurrentPDFPage();

        }
    );


/* =====================================================
   PDF KEYBOARD
===================================================== */

document.addEventListener(
    "keydown",
    async event => {

        if (
            detectBookType()
            !== "pdf"
        ) {

            return;

        }


        if (
            event.key === "ArrowRight"
            ||
            event.key === "PageDown"
        ) {

            event.preventDefault();

            if (
                pdfCurrentPage <
                pdfTotalPages
            ) {

                pdfCurrentPage++;

                await renderCurrentPDFPage();

            }

        }


        if (
            event.key === "ArrowLeft"
            ||
            event.key === "PageUp"
        ) {

            event.preventDefault();

            if (
                pdfCurrentPage > 1
            ) {

                pdfCurrentPage--;

                await renderCurrentPDFPage();

            }

        }

    }
);


/* =====================================================
   EPUB
===================================================== */

let epubBook = null;

let epubRendition = null;

let epubFontSize = 100;

let epubLineHeight = 1.5;

let epubMargin = 40;


async function loadEPUB() {

    epubReader.classList.remove(
        "hidden"
    );


    epubBook =
        ePub(bookUrl);


    epubRendition =
        epubBook.renderTo(
            "epubViewer",
            {

                width: "100%",

                height: "100%",

                spread: "none"

            }
        );


    applyEPUBTheme();


    await epubBook.ready;


    buildTOC();


    const book =
        getBookData();


    if (book.lastPosition) {

        await epubRendition.display(
            book.lastPosition
        );

    } else {

        await epubRendition.display();

    }


    epubRendition.on(
        "relocated",
        location => {

            handleEPUBLocation(
                location
            );

        }
    );


    epubRendition.on(
        "rendered",
        () => {

            applyEPUBTheme();

        }
    );

}


function handleEPUBLocation(
    location
) {

    if (
        !location
        || !location.start
    ) {

        return;

    }


    const percentage =
        Math.round(
            (
                location.start
                    .percentage || 0
            ) * 100
        );


    document.getElementById(
        "epubProgress"
    ).textContent =
        percentage + "%";


    document.getElementById(
        "epubProgressBar"
    ).style.width =
        percentage + "%";


    updateBookData({

        progress: percentage,

        lastPosition:
            location.start.cfi,

        completed:
            percentage >= 100

    });

}


/* =====================================================
   EPUB NAVIGATION
===================================================== */

document
    .getElementById("epubPrevious")
    .addEventListener(
        "click",
        () => {

            if (epubRendition) {

                epubRendition.prev();

            }

        }
    );


document
    .getElementById("epubNext")
    .addEventListener(
        "click",
        () => {

            if (epubRendition) {

                epubRendition.next();

            }

        }
    );


/* =====================================================
   EPUB TOC
===================================================== */

async function buildTOC() {

    const tocList =
        document.getElementById(
            "tocList"
        );


    tocList.innerHTML = "";


    const navigation =
        await epubBook.loaded.navigation;


    navigation.toc.forEach(
        item => {

            const button =
                document.createElement(
                    "button"
                );


            button.className =
                "toc-item";


            button.textContent =
                item.label;


            button.addEventListener(
                "click",
                () => {

                    epubRendition.display(
                        item.href
                    );

                }
            );


            tocList.appendChild(
                button
            );

        }
    );

}


/* =====================================================
   EPUB FONT
===================================================== */

document
    .getElementById("fontIncrease")
    .addEventListener(
        "click",
        () => {

            epubFontSize =
                Math.min(
                    epubFontSize + 10,
                    180
                );


            applyEPUBTypography();

        }
    );


document
    .getElementById("fontDecrease")
    .addEventListener(
        "click",
        () => {

            epubFontSize =
                Math.max(
                    epubFontSize - 10,
                    70
                );


            applyEPUBTypography();

        }
    );


function applyEPUBTypography() {

    if (!epubRendition) {
        return;
    }


    epubRendition.themes.fontSize(
        epubFontSize + "%"
    );


    document.getElementById(
        "fontSizeValue"
    ).textContent =
        epubFontSize + "%";


    epubRendition.themes.override(
        "line-height",
        epubLineHeight
    );


    epubRendition.themes.override(
        "padding",
        `0 ${epubMargin}px`
    );

}


/* =====================================================
   LINE SPACING
===================================================== */

document
    .getElementById("lineSpacing")
    .addEventListener(
        "input",
        event => {

            epubLineHeight =
                Number(
                    event.target.value
                );


            document.getElementById(
                "lineSpacingValue"
            ).textContent =
                epubLineHeight.toFixed(1);


            applyEPUBTypography();

        }
    );


/* =====================================================
   MARGINS
===================================================== */

document
    .getElementById("pageMargin")
    .addEventListener(
        "input",
        event => {

            epubMargin =
                Number(
                    event.target.value
                );


            document.getElementById(
                "pageMarginValue"
            ).textContent =
                epubMargin + "px";


            applyEPUBTypography();

        }
    );


/* =====================================================
   EPUB THEMES
===================================================== */

let currentTheme =
    localStorage.getItem(
        "readerTheme"
    ) || "light";


function applyEPUBTheme() {

    if (!epubRendition) {
        return;
    }


    let background;

    let text;


    if (currentTheme === "dark") {

        background = "#1b1b1b";

        text = "#eeeeee";

    }

    else if (
        currentTheme === "sepia"
    ) {

        background = "#f4ecd8";

        text = "#40382f";

    }

    else {

        background = "#ffffff";

        text = "#202124";

    }


    epubRendition.themes.default({

        body: {

            "background":
                background + " !important",

            "color":
                text + " !important"

        },

        "p, div": {

            "color":
                text + " !important"

        }

    });


    document.documentElement.style
        .setProperty(
            "--reader-background",
            background
        );


    document.documentElement.style
        .setProperty(
            "--reader-text",
            text
        );


    applyEPUBTypography();

}


document
    .querySelectorAll(
        ".theme-option"
    )
    .forEach(
        button => {

            button.addEventListener(
                "click",
                () => {

                    currentTheme =
                        button.dataset.theme;


                    localStorage.setItem(
                        "readerTheme",
                        currentTheme
                    );


                    applyEPUBTheme();

                    applyGlobalTheme();

                }
            );

        }
    );


/* =====================================================
   GLOBAL THEME
===================================================== */

function applyGlobalTheme() {

    document.body.dataset.theme =
        currentTheme;


    if (
        currentTheme === "dark"
    ) {

        document.body.style
            .setProperty(
                "--background",
                "#101114"
            );

    }

    else if (
        currentTheme === "sepia"
    ) {

        document.body.style
            .setProperty(
                "--background",
                "#3e382e"
            );

    }

    else {

        document.body.style
            .setProperty(
                "--background",
                "#0f1115"
            );

    }

}


function restoreTheme() {

    applyGlobalTheme();

}


/* =====================================================
   SETTINGS
===================================================== */

document
    .getElementById("settingsButton")
    .addEventListener(
        "click",
        () => {

            settingsPanel.classList.toggle(
                "hidden"
            );

        }
    );


document
    .getElementById("epubSettings")
    .addEventListener(
        "click",
        () => {

            settingsPanel.classList.toggle(
                "hidden"
            );

        }
    );


document
    .getElementById("closeSettings")
    .addEventListener(
        "click",
        () => {

            settingsPanel.classList.add(
                "hidden"
            );

        }
    );


document
    .getElementById("themeButton")
    .addEventListener(
        "click",
        () => {

            const order = [
                "light",
                "sepia",
                "dark"
            ];


            const currentIndex =
                order.indexOf(
                    currentTheme
                );


            currentTheme =
                order[
                    (
                        currentIndex + 1
                    ) % order.length
                ];


            localStorage.setItem(
                "readerTheme",
                currentTheme
            );


            applyEPUBTheme();

            applyGlobalTheme();

        }
    );


/* =====================================================
   FULLSCREEN
===================================================== */

document
    .getElementById("fullscreenButton")
    .addEventListener(
        "click",
        async () => {

            try {

                if (
                    !document.fullscreenElement
                ) {

                    await document.documentElement
                        .requestFullscreen();

                } else {

                    await document.exitFullscreen();

                }

            } catch (error) {

                console.error(
                    "Fullscreen error:",
                    error
                );

            }

        }
    );


/* =====================================================
   START
===================================================== */

initializeReader();